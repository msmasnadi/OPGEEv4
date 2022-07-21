import numpy as np
import os
import pandas as pd
from pathlib import Path
import ray
from ray.util.actor_pool import ActorPool
from time import sleep

from ..core import OpgeeObject
from ..log  import getLogger
from .simulation import Simulation

_logger = getLogger(__name__)

@ray.remote
class Worker(OpgeeObject):

    def __init__(self, sim_dir):
        self.sim = Simulation(sim_dir)

    @ray.method(num_returns=1)
    def run_field(self, field_name):
        """
        Run an MCS on the named field.

        :param field_name: (str) the name of the field to run
        :return: None
        """
        _logger.info(f"Running MCS for field '{field_name}'")
        field = self.sim.analysis.get_field(field_name)
        self.sim.run_field(field)
        _logger.info(f"Worker completed MCS on field '{field_name}'")
        return field_name


class Manager(OpgeeObject):
    def __init__(self):
        pass

    def start_cluster(self, num_cpus=None):
        if not ray.is_initialized():
            _logger.info("Starting ray processes...")
            ray.init(num_cpus=num_cpus)
            _logger.info("Ray has started.")

    def stop_cluster(self):
        _logger.info("Stopping ray processes...")
        ray.shutdown()
        _logger.info("Ray has stopped.")

    def run_mcs(self, sim_dir, field_names=None, cpu_count=0):
        from ..config import getParamAsInt

        # ray.init(num_cpus=4) on mac limits to 4 processes; default is 8, num cpus
        cpus = cpu_count or getParamAsInt('OPGEE.CPUsToUse') or os.cpu_count()

        self.start_cluster(num_cpus=cpu_count)
        sim = Simulation(sim_dir)

        # Caller can specify a subset of possible fields to run. Default is to run all.
        field_names = field_names or sim.field_names

        # TBD: check for unknown field names

        # Start the worker processes
        actors = [Worker.remote(sim_dir) for _ in range(cpus)]
        pool = ActorPool(actors)

        # _logger.debug("sleep(3)")
        #sleep(3)    # TBD: necessary?

        pool.submit(lambda actor, value: actor.run_field.remote(value), field_names)

        fields_to_run = set(field_names)

        while fields_to_run:
            if pool.has_next():
                field_name = pool.get_next()
                _logger.info(f"Worker.run_field returned for '{field_name}'")
                fields_to_run.discard(field_name)

            if pool.has_free():
                _logger.info("Popping idle Worker")
                pool.pop_idle()

        _logger.info("Workers finished")
        self.stop_cluster()

# def run_field_distributed(self, field, trial_nums):
#     """
#     Parallelization strategy is simply to run all the trials for each field on
#     a separate processor.
#
#     :param field:
#     :param trial_nums:
#     :return:
#     """
#     # Aggregate all of the results.
#     results = ray.get([actor.run_trial.remote(field, split) for actor, split in zip(actors, splits)])
#
#     cols = ['trial_num',
#             'CI',
#             'total_GHG',
#             'combustion',
#             'land_use',
#             'VFF',
#             'other']
#
#     df = pd.DataFrame.from_records(results, columns=cols)
#     # mkdirs(self.results_dir)
#     pathname = Path(self.results_dir) / (field.name + '.csv')
#     _logger.info(f"Writing '{pathname}'")
#     df.to_csv(pathname, index=False)
#
#     # ray.shutdown()
