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
from glob import glob
import os
import pandas as pd
import re
from typing import Sequence

from .core import OpgeeObject, Timer
from .config import getParam, getParamAsInt, getParamAsBoolean, pathjoin
from .constants import CLUSTER_NONE, SIMPLE_RESULT, DETAILED_RESULT, ERROR_RESULT
from .error import McsSystemError, AbstractMethodError
from .field import FieldResult
from .log import getLogger, setLogFile
from .model_file import extract_model
from .utils import flatten, pushd
from .mcs.simulation import Simulation, RESULTS_CSV, FAILURES_CSV

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

# From recipes at https://docs.python.org/3/library/itertools.html
def _batched(iterable, length):
    """
    Batch data into tuples of length n. The last batch may be shorter.
    Example: batched('ABCDEFG', 3) --> ABC DEF G
    """
    from itertools import islice

    if length < 1:
        raise ValueError('_batched: length must be > 0')

    it = iter(iterable)
    while batch := tuple(islice(it, length)):
        yield batch


class AbsPacket(OpgeeObject):
    """
    Abstract superclass for FieldPacket and TrialPacket
    """
    _next_packet_num: int = 1

    def __init__(self, items):
        self.items = items
        self.packet_num = AbsPacket._next_packet_num
        AbsPacket._next_packet_num += 1

    def __str__(self):  # pragma: no cover
        return f"<{self.__class__.__name__} {self.packet_num} count:{len(self.items)}>"

    def __iter__(self):
        """
        Iterate over the field names
        """
        yield from self.items

    def run(self, result_type):
        """
        Must be implemented by subclass.

        Run the trials in ``packet``, serially. In distributed mode,
        this set of runs is performed on a single worker process.

        :param result_type: (str) the type of results to return, i.e.
          SIMPLE_RESULT or DETAILED_RESULT
        :return: (list of FieldResult)
        """
        raise AbstractMethodError(self.__class__, 'run')

    def packetize(self, *args, **kwargs):
        "Must be implemented by subclass"
        raise AbstractMethodError(self.__class__, 'packetize')


class FieldPacket(AbsPacket):
    def __init__(self,
                 model_xml_file: str,
                 analysis_name: str,             # TBD: might not be needed here
                 field_names: Sequence[str]):
        """
        Create a ``FieldPacket`` of OPGEE runs to perform on a worker process.
        FieldPackets are defined by a list of field names. The worker process will
        iterate over the list of field names.

        :param analysis_name: (str) the name of the ``Analysis`` the runs are using
        :param field_names: (list of str) names of fields to iterate over for non-MCS
        """
        super().__init__(field_names)
        self.model_xml_file = model_xml_file
        self.analysis_name = analysis_name

    @classmethod
    def packetize(cls,
                  model_xml_file: str,
                  analysis_name: str,
                  field_names: Sequence[str],
                  packet_size: int):
        """
        Packetizes over ``field_names``. Each packet contains a set of
        field names to iterate over.
        """
        packets = [FieldPacket(model_xml_file, analysis_name, field_names)
                   for field_names in _batched(field_names, packet_size)]
        return packets

    def run(self, result_type):
        timer = Timer(f"FieldPacket.run({self})")
        field_names = self.items
        results = run_serial(self.model_xml_file, self.analysis_name, field_names,
                             result_type=result_type)
        timer.stop()

        _logger.debug(f"FieldPacket.run({self}) returning {len(results)} results")
        return results


class TrialPacket(AbsPacket):
    def __init__(self, sim_dir: str, field_name: str, trial_nums: Sequence[int]):
        super().__init__(trial_nums)
        self.sim_dir = sim_dir
        self.field_name = field_name

    @classmethod
    def packetize(cls,
                  sim_dir: str,
                  trial_nums: Sequence[int],
                  field_names: Sequence[str],
                  packet_size: int):
        """
        Packetizes over ``trial_nums`` for each name in ``field_names``.
        Each resulting packet identifies a set of trials for one field.
        """
        packets = [TrialPacket(sim_dir, field_name, trial_batch)
                   for field_name in field_names
                   for trial_batch in _batched(trial_nums, packet_size)]
        return packets

    def run(self, result_type):
        """
        Run the trials in ``packet``, serially. In distributed mode,
        this set of runs is performed on a single worker process.

        :param result_type: (str) the type of results to return, i.e.
          SIMPLE_RESULT or DETAILED_RESULT
        :return: (list of FieldResult)
        """
        timer = Timer(f"TrialPacket.run({self})")

        field_name = self.field_name

        sim_dir = self.sim_dir
        sim = Simulation(sim_dir, field_names=[field_name], save_to_path="")
        field_dir = Simulation.field_dir_path(sim_dir, field_name)
        log_file = f"{field_dir}/packet-{self.packet_num}.log"
        setLogFile(log_file, remove_old_file=True)

        _logger.info(f"Running MCS for field '{field_name}'")

        results = sim.run_packet(self, result_type)
        timer.stop()

        _logger.debug(f"TrialPacket.run({self}) returning {len(results)} results")
        return results



class Manager(OpgeeObject):
    def __init__(self, cluster_type=None):
        from .constants import CLUSTER_TYPES
        cluster_type = (cluster_type or getParam('OPGEE.ClusterType')).lower()

        if cluster_type not in CLUSTER_TYPES:
            raise McsSystemError(f"Unknown cluster type '{cluster_type}'. "
                                 f"Valid options are {CLUSTER_TYPES}.")

        self.cluster_type = cluster_type
        self.cluster = None
        self.client = None

    def __str__(self):
        cls = self.__class__.__name__
        return f"<{cls} cluster:{self.cluster_type}>"

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

    def run_packets(self,
                    packets: list[AbsPacket],
                    result_type: str = None,
                    num_engines: int = 0,
                    minutes_per_task: int = 10):
        """
        Run a set of packets (i.e., FieldPackets or TrialPackets) on a dask cluster.
        Yields each packet's results as they are available.

        :param packets: (list of AbsPacket) the packets describing model runs to execute
        :param result_type: (str) either SIMPLE_RESULT or DETAILED_RESULT.
        :param num_engines: (int) the number of worker tasks to start
        :param minutes_per_task: (int) how many minutes of walltime to allocate for each worker.
        :return: (list of FieldResult) results for individual runs.
        """
        timer = Timer('Manager.run_packets')

        result_type = result_type or SIMPLE_RESULT

        # This is useful mainly for testing. Any real MCS will use a proper cluster.
        if self.cluster_type == CLUSTER_NONE:
            for pkt in packets:
                results = pkt.run(result_type)
                yield results

            _logger.debug("Finished running packets (no cluster)")

        else:
            # N.B. start_cluster saves client in self.client and returns it as well
            client = self.start_cluster(num_engines=num_engines, minutes_per_task=minutes_per_task)

            # Start the worker processes on all available CPUs.
            futures = client.map(lambda pkt: pkt.run(result_type),packets)

            for future, results in as_completed(futures, with_results=True):
                yield results

            _logger.debug("Workers finished")
            self.stop_cluster()

        _logger.info(timer.stop())
        return None

def _run_field(analysis_name, field_name, xml_string, result_type,
               use_default_model=True):
    """
    Run a single field, once, using the model in ``xml_string`` and return a
    ``FieldResult`` instance with results of ``result_type``.

    :param analysis_name: (str) the name of the ``Analysis`` to use to run the ``Field``
    :param field_name: (str) the name of the ``Field`` to run
    :param xml_string: (str) XML description of the model to run
    :param result_type: (str) the type of results to return, i.e., "detailed"
        or "simple"
    :param use_default_model: (bool) whether to use the built-in model files.
    :return: (FieldResult) results of ``result_type`` or ERROR_RESULT, if an error
        occurred.
    """
    from .model_file import ModelFile

    try:
        mf = ModelFile.from_xml_string(xml_string, add_stream_components=False,
                                       use_class_path=False,
                                       use_default_model=use_default_model,
                                       analysis_names=[analysis_name],
                                       field_names=[field_name])

        analysis = mf.model.get_analysis(analysis_name)
        field = analysis.get_field(field_name)
        field.run(analysis)
        result = field.get_result(analysis, result_type)

    except Exception as e:
        result = FieldResult(analysis_name, field_name, ERROR_RESULT, error=str(e))

    return result

# TODO: could be method of Manager
def run_serial(model_xml_file, analysis_name, field_names, result_type=DETAILED_RESULT):
    timer = Timer('run_serial')

    results = []

    for field_name, xml_string in extract_model(model_xml_file, analysis_name,
                                                field_names):
        result = _run_field(analysis_name, field_name, xml_string, result_type)
        if result.error:
            _logger.error(f"Failed: {result}")

        results.append(result)

    _logger.info(timer.stop())
    return results

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
    if not results:
        _logger.debug("save_results received empty results list; nothing to do")
        return

    energy_cols = []
    emission_cols = []
    ci_rows = []
    error_rows = []

    for result in flatten(results):
        trial = result.trial_num

        if result.result_type == ERROR_RESULT:
            d = {"analysis": result.analysis_name,
                 "field": result.field_name,
                 "error": result.error}
            if trial is not None:
                d['trial'] = trial
            error_rows.append(d)
            continue

        if result.result_type != SIMPLE_RESULT:
            energy_cols.append(result.energy)
            emission_cols.append(result.emissions)

        for name, ci in result.ci_results:
            d = {"analysis": result.analysis_name,
                 "field": result.field_name,
                 "node": name,
                 "CI": ci}
            if trial is not None:
                d['trial'] = trial
            ci_rows.append(d)

    # Append batch number to filename if not None
    batch = '' if batch_num is None else f"_{batch_num}"

    def _to_csv(df, file_prefix, **kwargs):
        pathname = pathjoin(output_dir, f"{file_prefix}{batch}.csv")
        _logger.info(f"Writing '{pathname}'")
        df.to_csv(pathname, **kwargs)

    df = pd.DataFrame(data=ci_rows)
    _to_csv(df, 'carbon_intensity', index=False)

    if error_rows:
        df = pd.DataFrame(data=error_rows)
        _to_csv(df, 'errors', index=False)

    def _save_cols(columns, file_prefix):
        df = pd.concat(columns, axis="columns")
        df.index.name = "process"
        df.sort_index(axis="rows", inplace=True)
        _to_csv(df, file_prefix)

    # These aren't saved for SIMPLE_RESULTS
    if energy_cols:
        _save_cols(energy_cols, "energy")

    if emission_cols:
        _save_cols(emission_cols, "emissions")


def _combine_results(filenames, output_name, sort_by=None):
    if not filenames:
        return

    dfs = [pd.read_csv(name, index_col=False) for name in filenames]
    combined = pd.concat(dfs, axis='rows')

    if sort_by:
        combined.sort_values(sort_by, inplace=True)

    _logger.debug(f"Writing '{output_name}'")
    combined.to_csv(output_name, index=False)


results_pat  = re.compile(r'results-\d+\.csv$')
failures_pat = re.compile(r'failures-\d+\.csv$')

def combine_mcs_results(sim_dir, field_names, delete=False):
    """
    Combine CSV files containing partial results/failures from an MCS into two files,
    results.csv and failures.csv.

    :param sim_dir: (str) the simulation directory
    :param field_names: (list of str) names of fields to combine results for
    :param delete: (bool) whether to delete partial files after combining them
    :return: nothing
    """
    with pushd(sim_dir):
        for field_name in field_names:
            # TBD: handle case that field directory isn't present
            with pushd(field_name):
                # use glob with its limited wildcard capability, then filter for the real pattern
                result_files = [name for name in glob(r'results-*.csv') if re.match(results_pat, name)]
                _combine_results(result_files, RESULTS_CSV, sort_by='trial_num')

                failure_files = [name for name in glob(r'failures-*.csv') if re.match(failures_pat, name)]
                _combine_results(failure_files, FAILURES_CSV, sort_by='trial_num')

                if delete:
                    for name in result_files + failure_files:
                        os.remove(name)

def combine_field_results(output_dir, field_names, delete=False):
    """
    Combine CSV files containing partial results/failures from an MCS into two files,
    results.csv and failures.csv.

    :param sim_dir: (str) the simulation directory
    :param field_names: (list of str) names of fields to combine results for
    :param delete: (bool) whether to delete partial files after combining them
    :return: nothing
    """
    with pushd(output_dir):
        for field_name in field_names:
            with pushd(field_name):
                # use glob with its limited wildcard capability, then filter for the real pattern
                result_files = [name for name in glob(r'results-*.csv') if re.match(results_pat, name)]
                _combine_results(result_files, RESULTS_CSV)

                failure_files = [name for name in glob(r'failures-*.csv') if re.match(failures_pat, name)]
                _combine_results(failure_files, FAILURES_CSV)

                if delete:
                    for name in result_files + failure_files:
                        os.remove(name)
