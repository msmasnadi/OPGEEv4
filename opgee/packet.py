#
# AbsPacket class -- support for running a group of model runs on a worker process.
#
# Author: Richard Plevin
#
# Copyright (c) 2023 the author and The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from typing import Sequence
from .core import OpgeeObject, Timer
from .error import AbstractMethodError
from .log  import getLogger, setLogFile
_logger = getLogger(__name__)

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
        self.analysis_name = analysis_name

    @classmethod
    def packetize(cls, analysis_name: str, field_names: Sequence[str], packet_size: int):
        """
        Packetizes over ``field_names``. Each packet contains a set of
        field names to iterate over.
        """
        packets = [FieldPacket(analysis_name, field_names)
                   for field_names in _batched(field_names, packet_size)]
        return packets

    def run(self, result_type):
        timer = Timer(f"FieldPacket.run({self})")

        field_name = self.field_name

        log_file = f"{field_dir}/packet-{self.packet_num}.log"
        setLogFile(log_file, remove_old_file=True)

        for field_name in packet:
            try:
                # Reload from cached XML string to avoid stale state
                self.load_model()
                analysis = self.analysis

                # Use the new instance of field from the reloaded model
                field = analysis.get_field(field_name)

                self.set_trial_data(analysis, field, trial_num)

                field.run(analysis, compute_ci=True, trial_num=trial_num)
                result = field.get_result(analysis, result_type, trial_num=trial_num)
                results.append(result)

            except Exception as e:
                errmsg = f"Trial {trial_num}: {e}"
                result = FieldResult(self.analysis.name, field_name, ERROR_RESULT,
                                     trial_num=trial_num, error=errmsg)
                results.append(result)

                _logger.warning(f"Exception raised in trial {trial_num} in {field_name}: {e}")
                _logger.debug(traceback.format_exc())
                continue

        return results

        results = sim.run_packet(self, result_type)
        timer.stop()

        _logger.debug(f"FieldPacket.run({self}) returning {len(results)} results")
        return results


class TrialPacket(AbsPacket):
    def __init__(self, sim_dir: str, field_name: str, trial_nums: Sequence[int]):
        super().__init__(trial_nums)
        self.sim_dir = sim_dir
        self.field_name = field_name

    @classmethod
    def packetize(cls, sim_dir: str, field_names: Sequence[str], trial_nums: Sequence[int],
                  packet_size: int):
        """
        Packetizes over ``trial_nums`` for each name in ``field_names``.
        Each resulting packet identifies a set of trials for one field.
        """
        packets = [TrialPacket(sim_dir, field_name, trial_batch)
                   for field_name in field_names
                   for trial_batch in _batched(trial_nums, packet_size)]
        return packets

    # TBD: revise this to iterate over pkt.trial_nums or pkt.field_names and
    #   return a FieldResult. Should be no need for a RemoteError result.
    def run(self, result_type):
        """
        Run the trials in ``packet``, serially. In distributed mode,
        this set of runs is performed on a single worker process.

        :param result_type: (str) the type of results to return, i.e.
          SIMPLE_RESULT or DETAILED_RESULT
        :return: (list of FieldResult)
        """
        from .mcs.simulation import Simulation

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
