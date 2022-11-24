import ipyparallel as ipp
import os
import re
import traceback

from ..core import OpgeeObject, Timer
from ..config import getParam
from ..error import OpgeeException, RemoteError, McsUserError, McsSystemError
from ..log  import getLogger
from .simulation import Simulation

_logger = getLogger(__name__)

DEFAULT_NUM_ENGINES = 4

# This isn't used yet
# def find_object(analysis, field, obj_name):             # pragma: no cover
#     name = obj_name.lower()     # TBD: document this
#
#     if name == 'analysis':
#         obj = analysis
#
#     elif name == 'field':
#         obj = field
#
#     elif (m := re.match('(\w+)\[(\w+)\]', name)):
#         class_name = m(1)
#         item_name  = m(2)
#
#         known_class_names = ('Container', 'Process', 'Stream')  # TBD: make this extensible via config vars
#         if not class_name in known_class_names:
#             raise McsUserError(f"Unknown object name for MCS results: '{class_name}'")
#
#         # TBD: make extensible
#         if class_name == 'Container':
#             # TBD: maybe have an agg_dict in addition to aggs at each level? Enforce unique naming
#             theDict = field.aggs
#             theDict = field.agg_dict
#         elif class_name == 'Process':
#             theDict = field.process_dict
#         elif class_name == 'Stream':
#             theDict = field.stream_dict
#
#         if (obj := theDict.get(item_name)) is None:
#             raise McsUserError(f"{obj} doesn't have '{obj_name}'")
#
#     return obj

# This isn't used yet
# def parse_result_name(analysis, field, result_name):        # pragma: no cover
#     parts = result_name.split('.')
#     if not parts:
#         raise McsUserError(f"Result names must have at least 2 dot-delimited parts. Got '{result_name}'")
#     obj_name = parts[0]
#     obj = find_object(analysis, field, obj_name)
#
#     # ask obj (the found object) to return the value for parts[1:]


class FieldResult(OpgeeObject):
    __slots__ = ['ok', 'field_name', 'duration', 'error']

    def __init__(self, field_name, duration, error=None):
        self.ok = error is None
        self.field_name = field_name
        self.duration = duration
        self.error = error

    def __str__(self):
        return f"<FieldResult {self.field_name} in {self.duration}; error:{self.error}>"


# Used only for debugging, no need for test coverage
class LocalWorker(OpgeeObject):        # pragma: no cover
    def __init__(self, sim_dir):
        self.sim = Simulation(sim_dir, save_to_path='')

    def run_field(self, field_name, trial_nums=None):
        """
        Run an MCS on the named field.

        :param field_name: (str) the name of the field to run
        :return: None
        """
        timer = Timer('run_field').start()

        field = self.sim.analysis.get_field(field_name)
        if field.is_enabled():
            _logger.info(f"Running MCS for field '{field_name}'")

            error = None
            try:
                self.sim.run_field(field, trial_nums=trial_nums)

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
        _logger.debug(f"LocalWorker.run_field('{field_name}') returning {result}")
        return result

class Worker(LocalWorker):
    """
    Same as above, but using ray.
    """
    def __init__(self, sim_dir):
        super().__init__(sim_dir)

    def run_field(self, field_name, trial_nums=None):
        try:
            return super().run_field(field_name, trial_nums=trial_nums)
        except Exception as e:
            e_name = e.__class__.__name__
            trace = ''.join(traceback.format_stack())
            _logger.error(f"In Worker.run_field('{field_name}'): {e_name}: {e}\n{trace}")
            raise e

MCS_MODE_LOCAL = 'local'
MCS_MODE_CLUSTER = 'cluster'

# TBD: bring over code from pygcam; much of it is useful, though some could be updated (and ported back?)
class Manager(OpgeeObject):
    def __init__(self, profile=None, mode=MCS_MODE_LOCAL):
        self.profile = profile or getParam('IPP.Profile')
        self.cluster = None
        self.client = None

        valid = (MCS_MODE_LOCAL, MCS_MODE_CLUSTER)
        if mode not in valid:
            raise McsSystemError(f"Valid modes for MCS Manager are {valid}; got '{mode}'")

        self.mode = mode

    def connect_to_cluster(self):
        """
        Connect to the cluster assumed to be already running at address $RAY_ADDRESS.
        """
        _logger.debug(f"Connecting to IPP cluster '{self.profile}'")
        self.client = self.cluster.connect_client()
        return self.client

    def start_cluster(self, num_engines=DEFAULT_NUM_ENGINES):
        if not self.cluster:
            _logger.info(f"Creating IPP cluster '{self.profile}")
            self.cluster = ipp.Cluster(profile=self.profile, n=num_engines)

        _logger.info(f"Starting IPP cluster '{self.profile}")
        self.client = self.cluster.start_and_connect_sync()
        return self.client

    async def stop_cluster(self):
        _logger.info("Stopping IPP cluster")
        await self.cluster.stop_cluster()

    def run_mcs(self, sim_dir, field_names=None, num_engines=0, trial_nums=None, debug=False):
        from ..utils import parseTrialString

        timer = Timer('Manager.run_mcs').start()

        sim = Simulation(sim_dir, save_to_path='')

        trial_nums = range(sim.trials) if trial_nums == 'all' else parseTrialString(trial_nums)

        # Caller can specify a subset of possible fields to run. Default is to run all.
        # TBD: check for unknown field names
        field_names = field_names or sim.field_names

        if debug:
            # test worker in current process for debugging
            w = LocalWorker(sim_dir)
            for field_name in field_names:
                result = w.run_field(field_name, trial_nums=trial_nums)
                _logger.info(f"Completed MCS on field '{result.field_name}' in {int(result.duration)}")

        else:
            client = self.start_cluster(num_engines=num_engines)
            view = client.direct_view()

            # Start the worker processes on all available CPUs
            # workers = [Worker.remote(sim_dir) for _ in range(cpus)]

            def submit(worker, field_name):
                return worker.run_field.remote(field_name, trial_nums=trial_nums)

            # async_results = dv.apply_sync(lambda: run_field(field_name, trial_nums=trial_nums)

            # See pygcam.mcs.master.Master
            # result = view.map_async(worker.runTrial, [context], [argDict])

            # while True:
            #     try:
            #         result = pool.get_next_unordered()
            #         _logger.info(f"Worker completed MCS: {result}")
            #
            #     except StopIteration:
            #         _logger.debug("No more results to get")
            #         break
            #
            #     except Exception as e:
            #         _logger.error(f"Failed get_next_unordered: {e}")
            #         traceback.print_exc()

            _logger.debug("Workers finished")
            self.stop_cluster()

        _logger.info(timer.stop())
