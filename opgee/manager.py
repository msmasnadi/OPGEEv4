#
# manager.py -- implements running a distributed computation using dask.
#
# Author: Richard Plevin
#
# Copyright (c) 2023 the author and The Board of Trustees of the Leland Stanford
# Junior University. See LICENSE.txt for license details.
#
import asyncio
import dask
from dask_jobqueue import SLURMCluster
from dask.distributed import Client, LocalCluster, as_completed
import pandas as pd

from .core import OpgeeObject, Timer, magnitude
from .config import getParam, getParamAsInt, getParamAsBoolean, pathjoin
from .error import OpgeeException, McsSystemError
from .field import SIMPLE_RESULT, DETAILED_RESULT, ERROR_RESULT, ALL_RESULT_TYPES
from .log import getLogger #, setLogFile
from .packet import AbsPacket


# To debug dask, uncomment the following 2 lines
# import logging
# logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

_logger = getLogger(__name__)

def _walltime(minutes: int) -> str:
    """
    Convert minutes to a walltime string suitable for SLURM

    :param minutes: (int) a number of minutes
    :return: (str) a string of the form "HH:MM:00"
    """
    return f"{minutes // 60 :02d}:{minutes % 60 :02d}:00"


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

    # TBD: Model this after (or merge with) simulation.run_parallel using yield
    #   Convert to yielding results to caller can save in batches
    def run_packets(self,
                    packets: list[AbsPacket],
                    result_type: str = None,
                    num_engines: int = 0,
                    minutes_per_task: int = 10):
        """
        Run a set of packets (i.e., FieldPackets or TrialPackets) on a dask cluster.

        :param packets: (list of AbsPacket) the packets describing model runs to execute
        :param result_type: (str) either SIMPLE_RESULT or DETAILED_RESULT.
        :param num_engines: (int) the number of worker tasks to start
        :param minutes_per_task: (int) how many minutes of walltime to allocate for each worker.
        :return: (list of FieldResult) results for individual runs.
        """
        timer = Timer('Manager.run_packets')

        result_type = result_type or SIMPLE_RESULT

        # N.B. start_cluster saves client in self.client and returns it as well
        client = self.start_cluster(num_engines=num_engines, minutes_per_task=minutes_per_task)

        # Start the worker processes on all available CPUs.
        futures = client.map(lambda pkt: pkt.run(result_type),packets)
        results_list = []

        # TBD: modify to write CSV files here rather than in workers
        for future, results in as_completed(futures, with_results=True):
            # if result.error:
            #     _logger.error(f"Failed: {result}")
            #     #traceback.print_exc()
            # else:
            #     _logger.debug(f"Succeeded: {result}")

            # TBD: yield
            # yield results
            results_list.append(results)

        _logger.debug("Workers finished")

        # if collect:
        #     combine_results(sim_dir, field_names, delete=delete_partials)

        self.stop_cluster()
        _logger.info(timer.stop())

        # TBD: if yielding, return None here
        # return None
        return results_list

    # Deprecated
    # def run_mcs(self,
    #             packets: list[TrialPacket],
    #             result_type: str = SIMPLE_RESULT,
    #             num_engines: int = 0,
    #             minutes_per_task: int = None,
    #             # collect=False, delete_partials=False
    #             ):
    #     """
    #     Run a Monte Carlo simulation on a dask cluster.
    #
    #     :param field_names: (list of str) the names of the fields to run; empty list or ``None``
    #         implies use all fields found in the ``Simulation`` metadata.
    #     :param num_engines: (int) the number of worker tasks to start
    #     :param minutes_per_task: (int) how many minutes of walltime to allocate for each worker.
    #     :param collect: (bool) whether to combine all partial (packet) results and failures
    #         into a single results and single failures file.
    #     :param delete_partials: (bool) whether to delete partial result and failure files after
    #         combining them. Ignored if collect is False.
    #     :return: nothing
    #     """
    #     sim_dir = packets[0].sim_dir    # should be same for all packets
    #
    #     # Put the log for the monitor process in the simulation directory.
    #     # Workers will set the log file to within the directory for the
    #     # field it's currently running.
    #     log_file = f"{sim_dir}/opgee-mcs.log"
    #     setLogFile(log_file, remove_old_file=True)
    #
    #     results_list = self.run_packets(packets,
    #                                     result_type=result_type,
    #                                     num_engines=num_engines,
    #                                     minutes_per_task=minutes_per_task)
    #     return results_list
    #

def save_results(results, output_dir, batch_num=None):
    """
    Save "detailed" results, comprising top-level carbon intensity (CI) from
    ``results``, and per-process energy and emissions details. Results are
     written to CSV files under the directory ``output_dir``.

    :param results: (list[FieldResult]) results from running a ``Field``
    :param output_dir: (str) where to write the CSV files
    :param collect: (bool) whether to collect batched results into a
        single file
    :param batch_num: (int) if not None, a number to use in the CSV file
        name to distinguish partial result files.
    :return: none
    """
    energy_cols = []
    emission_cols = []
    ci_rows = []
    error_rows = []

    # TBD: might be lists of lists?
    # from .utils import flatten
    # for result in flatten(results):
    for result in results:

        trial = '' if result.trial_num is None else result.trial_num

        if result.result_type == ERROR_RESULT:
            d = {"analysis": result.analysis_name,
                 "field": result.field_name,
                 "trial" : trial,
                 "error": result.error}
            error_rows.append(d)
            continue

        energy_cols.append(result.energy)
        emission_cols.append(result.emissions)

        for name, ci in result.ci_results:
            d = {"analysis": result.analysis_name,
                 "field": result.field_name,
                 "trial" : trial,
                 "node": name,
                 "CI": ci}
            ci_rows.append(d)

    # Append batch number to filename if not None
    batch = '' if batch_num is None else f"_{batch_num}"

    def _to_csv(df, file_prefix, **kwargs):
        pathname = pathjoin(output_dir, f"{file_prefix}{batch}.csv")
        _logger.info(f"Writing '{pathname}'")
        df.to_csv(pathname, **kwargs)

    df = pd.DataFrame(data=ci_rows)
    _to_csv(df, 'carbon_intensity', index=False)

    df = pd.DataFrame(data=error_rows)
    _to_csv(df, 'errors', index=False)

    def _save_cols(columns, file_prefix):
        df = pd.concat(columns, axis="columns")
        df.index.name = "process"
        df.sort_index(axis="rows", inplace=True)
        _to_csv(df, file_prefix)

    _save_cols(energy_cols, "energy")
    _save_cols(emission_cols, "emissions")
