#
# AbsPacket class -- support for running a group of model runs on a worker process.
#
# Author: Richard Plevin
#
# Copyright (c) 2023 the author and The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from typing import Sequence

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


class AbsPacket():
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

