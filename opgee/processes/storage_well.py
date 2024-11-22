#
# StorageWell class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..emissions import EM_FUGITIVES
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class StorageWell(Process):
    """
    Storage well calculate fugitive emission from storage wells.

    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self._required_inputs = [
            "gas",
        ]

        self._required_outputs = [
            "gas",
        ]

        self.cache_attributes()

    def cache_attributes(self):
        self.loss_rate = self.venting_fugitive_rate()

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas")

        if input.is_uninitialized():
            return

        gas_fugitives = self.set_gas_fugitives(input, self.loss_rate)

        gas_to_separator = self.find_output_stream("gas")
        gas_to_separator.copy_gas_rates_from(input)
        gas_to_separator.subtract_rates_from(gas_fugitives)

        # emissions
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
