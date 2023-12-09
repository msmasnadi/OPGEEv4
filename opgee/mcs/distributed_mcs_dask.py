#
# distributed_mcs_dask -- implements running a distributed Monte Carlo simulation using dask.
#
# Author: Richard Plevin
#
# Copyright (c) 2023 the author and The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import asyncio
import dask
# from dask_jobqueue import SLURMCluster
from dask.distributed import Client, LocalCluster, as_completed
from itertools import islice, product

# To debug dask, uncomment the following 2 lines
# import logging
# logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

from ..core import OpgeeObject, Timer
from ..config import getParam, getParamAsInt, getParamAsBoolean
from ..error import RemoteError, McsSystemError, TrialErrorWrapper
from ..log  import getLogger, setLogFile
from .simulation import Simulation, combine_results

_logger = getLogger(__name__)

# From recipes at https://docs.python.org/3/library/itertools.html
def batched(iterable, n):
    "Batch data into tuples of length n. The last batch may be shorter."
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError('batched: n must be at least one')

    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


def _walltime(minutes: int) -> str:
    """
    Convert minutes to a walltime string suitable for SLURM

    :param minutes: (int) a number of minutes
    :return: (str) a string of the form "HH:MM:00"
    """
    return f"{minutes // 60 :02d}:{minutes % 60 :02d}:00"

# Global to track how many tasks each worker is running
_task_count = 0

class FieldResult(OpgeeObject):
    __slots__ = ['ok', 'field_name', 'packet_num', 'duration', 'completed', 'task_count', 'error']

    def __init__(self, field_name, duration, completed, packet_num=None, error=None):
        self.ok = error is None
        self.field_name = field_name
        self.packet_num = packet_num
        self.duration = duration
        self.completed = completed
        self.task_count = _task_count
        self.error = error

    def __str__(self):
        packet_info = "" if self.packet_num is None else f"[{self.packet_num}]"
        return f"<FieldResult {self.completed} trials of {self.field_name}{packet_info} in {self.duration}; task_count:{self.task_count} error:{self.error}>"

def run_field(sim_dir, field_name, trial_nums=None, packet_num=None):
    """
    Run the trials ``trial_nums`` for ``field``, serially. In distributed mode,
    this is run in each worker process.

    :param sim_dir: (str) the directory containing the simulation information
    :param field_name: (str) the name of the field to run
    :param trial_nums: (list of int) trial numbers to run. If ``None``, run all trials.
    :param packet_num: (int) if not None, the sequential number for this packet
      in ``field``. This is used to name files holding results for this packet.
    :return: (FieldResult)
    """
    timer = Timer('run_field').start()

    sim = Simulation(sim_dir, field_names=[field_name], save_to_path='')
    field = sim.analysis.get_field(field_name)

    if field.is_enabled():
        global _task_count
        _task_count += 1

        field_dir = sim.field_dir(field)
        log_file = f"{field_dir}/field-packet-{packet_num}.log"
        setLogFile(log_file, remove_old_file=True)

        _logger.info(f"Running MCS for field '{field_name}'")

        error = None
        try:
            completed = sim.run_field(field, trial_nums, packet_num=packet_num)

        except TrialErrorWrapper as e:
            trial = e.trial
            e = e.error
            e_name = e.__class__.__name__
            _logger.error(f"In run_field('{field_name}'): trial={trial} {e_name}: {e}")
            error = RemoteError(f"{e_name}: {e}", field_name, trial=trial)

        except Exception as e:
            # Convert any exceptions to a RemoteError instance and return it to Manager
            e_name = e.__class__.__name__

            # show_trace = False  # turns out not to be very informative
            # trace =  '\n' + ''.join(traceback.format_stack()) if show_trace else ''
            # _logger.error(f"In run_field('{field_name}'): {e_name}: {e}{trace}")

            _logger.error(f"In run_field('{field_name}'): {e_name}: {e}")
            error = RemoteError(f"{e_name}: {e}", field_name)

    else:
        error = RemoteError(f"Ignoring disabled field {field}", field_name)

    timer.stop()

    result = FieldResult(field_name, timer.duration(), completed, error=error)
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

        cores = getParamAsInt('SLURM.CoresPerNode') # "Total number of cores per job"

        if cluster_type == 'slurm':
            # "Cut the job up into this many processes. Good for GIL workloads or for nodes with
            #  many cores. By default, process ~= sqrt(cores) so that the number of processes and
            #  the number of threads per process is roughly the same."
            processes_per_core = getParamAsInt('SLURM.ProcessesPerCore')
            processes = cores // processes_per_core
            shell = getParam('SLURM.Shell')

            # N.B. "Failed to launch worker. You cannot use the --no-nanny argument when n_workers > 1."
            nanny = getParamAsBoolean('SLURM.UseNanny')  # "Whether to start a nanny process"

            job_script_prologue = None # ['conda activate opgee'] failed
            minutes_per_task = minutes_per_task or getParamAsInt("SLURM.MinutesPerTask")

            arg_dict = dict(
                account = getParam('SLURM.Account') or None,
                job_name = getParam('SLURM.JobName'),
                queue = getParam('SLURM.Partition'),
                walltime = _walltime(minutes_per_task),
                cores=cores,
                processes=processes,
                memory = getParam('SLURM.MemPerJob'),
                local_directory = getParam('SLURM.TempDir'),
                interface = getParam('SLURM.Interface') or None,
                shebang = '#!' + shell if shell else None,
                nanny = nanny,  # can't seem to get nanny = False to work...
                job_script_prologue = job_script_prologue,
            )

            _logger.debug(f"calling SLURMCluster({arg_dict})")

            # n_workers: "Number of workers to start by default. Defaults to 0. See the scale method"
            cluster = SLURMCluster(**arg_dict)
            _logger.debug(cluster.job_script())

            _logger.debug(f"calling cluster.scale(cores={num_engines})")
            cluster.scale(cores=num_engines)  # scale up to the desired total number of cores

        elif cluster_type == 'local':
            # Set processes=False and swap n_workers and threads_per_worker to use threads in one
            # process, which is helpful for debugging. Note that some packages are not thread-safe.
            # Running with n_workers=1, threads_per_worker=2 resulted in weird runtime errors in Chemical.
            # self.cluster = cluster = LocalCluster(n_workers=1, threads_per_worker=num_engines, processes=False)

            self.cluster = cluster = LocalCluster(n_workers=num_engines, threads_per_worker=1, processes=True)

        else:
            raise McsSystemError(f"Unknown cluster type '{cluster_type}'. Valid options are 'slurm' and 'local'.")

        _logger.info(f"Starting {cluster_type } cluster")
        self.client = client = Client(cluster)

        _logger.info("Waiting for workers")
        while True:
            try:
                # print('.', sep='', end='')
                client.wait_for_workers(1, 15) # wait for 1 worker with 15 sec timeout
                break
            except (dask.distributed.TimeoutError, asyncio.exceptions.TimeoutError) as e:
                pass
                #print(e) # prints "Only 0/1 workers arrived after 15"

        _logger.info("Workers are running")
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

    def run_mcs(self, sim_dir, packet_size : int, field_names=None, num_engines=0,
                trial_nums=None, minutes_per_task=None, collect=False,
                delete_partials=False):
        """
        Run a Monte Carlo simulation on a dask cluster.

        :param sim_dir: (str) the directory containing the simulation information
        :param packet_size: (int) the target number of trials to run serially on a worker task.
        :param field_names: (list of str) the names of the fields to run
        :param num_engines: (int) the number of worker tasks to start
        :param trial_nums: (list of int) trial numbers to run. If ``None``, run all trials.
        :param minutes_per_task: (int) how many minutes of walltime to allocate for each worker.
        :param collect: (bool) whether to combine all partial (packet) results and failures
            into a single results and single failures file.
        :param delete_partials: (bool) whether to delete partial result and failure files after
            combining them. Ignored if collect is False.
        :return: nothing
        """
        from ..utils import parseTrialString

        timer = Timer('Manager.run_mcs').start()

        sim = Simulation(sim_dir, field_names=field_names, save_to_path='')

        # Put the log for the monitor process in the simulation directory.
        # Workers will set the log file to within the directory for the
        # field it's currently running.
        log_file = f"{sim_dir}/opgee-mcs.log"
        setLogFile(log_file, remove_old_file=True)

        trial_nums = range(sim.trials) if trial_nums == 'all' else parseTrialString(trial_nums)

        # TBD: check for unknown field names
        # Caller can specify a subset of possible fields to run. Default is to run all.
        field_names = field_names or sim.field_names

        # N.B. start_cluster saves client in self.client and returns it as well
        client = self.start_cluster(num_engines=num_engines, minutes_per_task=minutes_per_task)

        # Split trial_nums into packets of max 'packet_size'
        packets = batched(trial_nums, packet_size)

        def _run_field(tup):
            field_name, (packet_num, trial_nums) = tup

            return run_field(sim_dir, field_name,
                             trial_nums=trial_nums,
                             packet_num=packet_num)

        # Start the worker processes on all available CPUs.
        # Note that "list(product())" is required since map doesn't support iterators.
        futures = client.map(_run_field, list(product(field_names, enumerate(packets))))

        for future, result in as_completed(futures, with_results=True):
            if result.error:
                _logger.error(f"Failed: {result}")
                #traceback.print_exc()
            else:
                _logger.debug(f"Succeeded: {result}")

        _logger.debug("Workers finished")

        if collect:
            combine_results(sim_dir, field_names, delete=delete_partials)

        self.stop_cluster()
        _logger.info(timer.stop())

