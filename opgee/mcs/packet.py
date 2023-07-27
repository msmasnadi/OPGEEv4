#
# Packet class -- support for running a group of model runs on a worker process.
#
# Author: Richard Plevin
#
# Copyright (c) 2023 the author and The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..error import OpgeeException


class Packet:
    next_packet_num: int = 1

    def __init__(
        self,
        analysis_name: str,             # TBD: might not be needed here
        trial_nums: list[int] = None,
        field_name: str = None,
        field_names: list[str] = None,
    ):
        """
        Create a ``Packet`` of OPGEE runs to perform on a worker process. Packets
        are defined by either a list of trial numbers (which implies a Monte Carlo
        simulation) or a list of field names. The worker process will iterate over
        the list of trial numbers for the MCS case, or the list of field names for
        the non-MCS case.

        :param analysis_name: (str) the name of the ``Analysis`` the runs are using
        :param trial_nums: (list of int) trial numbers for Monte Carlo simulations
        :param field_name: (str) the name of a single field to use with MCS
        :param field_names: (list of str) names of fields to iterate over for non-MCS
        """
        if not (field_names or (trial_nums and field_name)):
            raise OpgeeException(
                "Packet must be initialized with trial_nums and field_name, or field_names."
            )

        if trial_nums and field_names:
            raise OpgeeException(
                "Packet must be initialized with either trial_nums or field_names, not both."
            )

        self.count = len(trial_nums or field_names)

        self.analysis_name = analysis_name
        self.field_names = field_names
        self.trial_nums = trial_nums
        self.field_name = field_name

        self.packet_num = Packet.next_packet_num
        Packet.next_packet_num += 1

    def __str__(self):  # pragma: no cover
        return f"<Packet {self.packet_num}, analysis:{self.analysis_name}, is_mcs:{self.is_mcs}>"

    @property
    def is_mcs(self):
        return self.trial_nums is not None

    def __iter__(self):
        """
        Iterate over the trial numbers or the field names.
        """
        source = self.trial_nums or self.field_names
        yield from source
