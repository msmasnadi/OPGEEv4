import dask
from dask_jobqueue import SLURMCluster
from dask.distributed import Client, LocalCluster, as_completed
import traceback

from ..core import OpgeeObject, Timer
from ..config import getParam, getParamAsInt
from ..error import RemoteError, McsSystemError
from ..log  import getLogger
from .simulation import Simulation

_logger = getLogger(__name__)

def _walltime(minutes: int) -> str:
    """
    Convert minutes to a walltime string suitable for SLURM

    :param minutes: (int) a number of minutes
    :return: (str) a string of the form "HH:MM:00"
    """
    return f"{minutes // 60 :02d}:{minutes % 60 :02d}:00"

class FieldResult(OpgeeObject):
    __slots__ = ['ok', 'field_name', 'duration', 'error']

    def __init__(self, field_name, duration, error=None):
        self.ok = error is None
        self.field_name = field_name
        self.duration = duration
        self.error = error

    def __str__(self):
        return f"<FieldResult {self.field_name} in {self.duration}; error:{self.error}>"


def run_field(sim_dir, field_name, trial_nums=None):
    """
    Run an MCS on the named field.

    :param sim_dir: (str) the directory containing the simulation information
    :param field_name: (str) the name of the field to run
    :return: (FieldResult)
    """
    timer = Timer('run_field').start()

    sim = Simulation(sim_dir, save_to_path='')

    field = sim.analysis.get_field(field_name)
    if field.is_enabled():
        _logger.info(f"Running MCS for field '{field_name}'")

        error = None
        try:
            sim.run_field(field, trial_nums=trial_nums)

        except Exception as e:
            # Convert any exceptions to a RemoteError instance and return it to Manager
            e_name = e.__class__.__name__
            trace = ''.join(traceback.format_stack())
            _logger.error(f"In LocalWorker.run_field('{field_name}'): {e_name}: {e}\n{trace}")
            error = RemoteError(f"{e_name}: {e}\n{trace}", field_name)

    else:
        error = RemoteError(f"Ignoring disabled field {field}", field_name)

    timer.stop()

    result = FieldResult(field_name, timer.duration(), error=error)
    _logger.debug(f"run_field('{field_name}') returning {result}")
    return result


class Manager(OpgeeObject):
    def __init__(self, cluster_type=None):
        cluster_type = (cluster_type or getParam('OPGEE.ClusterType')).lower()

        valid = ('local', 'slurm')
        if cluster_type not in valid:
            raise McsSystemError(f"Unknown cluster type '{cluster_type}'. Valid options are {valid}.")

        self.cluster_type = cluster_type
        self.cluster = None
        self.client = None

    def start_cluster(self, num_engines=None, minutes_per_task=None):
        cluster_type = self.cluster_type

        _logger.info(f"Creating {cluster_type} cluster")

        cores = getParamAsInt('SLURM.CoresPerNode')

        if cluster_type == 'slurm':
            minutes_per_task = minutes_per_task or getParamAsInt("SLURM.MinutesPerTask")
            memory = "2GiB"
            walltime = _walltime(minutes_per_task)
            account = getParam('SLURM.Account') or None
            local_directory = getParam('SLURM.TempDir')
            queue = getParam('SLURM.Partition')
            job_name = getParam('SLURM.JobName')

            _logger.debug(f"""SLURMCluster(cores={cores}, processes={cores}, memory='{memory}',
walltime='{walltime}', account='{account}', local_directory='{local_directory}', 
queue='{queue}', job_name='{job_name}')""")

            cluster = SLURMCluster(cores=cores, processes=cores, memory=memory,
                                   walltime=walltime, account=account,
                                   local_directory=local_directory,
                                   queue=queue, job_name=job_name)

        elif cluster_type == 'local':
            # Set processes=False and swap n_workers and threads_per_worker to use threads in one
            # process, which is helpful for debugging. Note that some packages are not thread-safe.
            # Running with n_workers=1, threads_per_worker=2 resulted in weird runtime errors in Chemical.
            # self.cluster = cluster = LocalCluster(n_workers=1, threads_per_worker=num_engines, processes=False)

            self.cluster = cluster = LocalCluster(n_workers=num_engines, threads_per_worker=1, processes=True)

        else:
            raise McsSystemError(f"Unknown cluster type '{cluster_type}'. Valid options are 'slurm' and 'local'.")

        cluster.scale(cores=num_engines)    # scale up to the desired total # of cores

        _logger.info(f"Starting {cluster_type } cluster")
        self.client = client = Client(cluster)

        _logger.info("Waiting for workers")
        while True:
            try:
                print('.', sep='', end='')
                client.wait_for_workers(1, 15) # wait for 1 worker with 15 sec timeout
                break
            except dask.distributed.TimeoutError as e:
                print(e)

        _logger.info("\nWorkers are running")
        return client

    def stop_cluster(self):
        from time import sleep

        _logger.info("Stopping cluster")
        self.client.close()
        sleep(5)
        self.client.shutdown()
        sleep(5)

        #self.client.retire_workers()
        #sleep(1)
        #self.client.scheduler.shutdown()

        self.client = self.cluster = None

    def run_mcs(self, sim_dir, field_names=None, num_engines=0, trial_nums=None,
                minutes_per_task=None):
        from ..utils import parseTrialString

        timer = Timer('Manager.run_mcs').start()

        sim = Simulation(sim_dir, field_names=field_names, save_to_path='')

        trial_nums = range(sim.trials) if trial_nums == 'all' else parseTrialString(trial_nums)

        # TBD: check for unknown field names
        # Caller can specify a subset of possible fields to run. Default is to run all.
        field_names = field_names or sim.field_names

        # N.B. start_cluster saves client in self.client and returns it as well
        client = self.start_cluster(num_engines=num_engines, minutes_per_task=minutes_per_task)

        def _run_field(field_name):
            return run_field(sim_dir, field_name, trial_nums=trial_nums)

        # Start the worker processes on all available CPUs
        futures = client.map(_run_field, field_names)

        for future, result in as_completed(futures, with_results=True):
            if result.error:
                _logger.error(f"Failed: {result}")
                #traceback.print_exc()
            else:
                _logger.debug(f"Succeeded: {result}")

        _logger.debug("Workers finished")

        self.stop_cluster()
        _logger.info(timer.stop())

