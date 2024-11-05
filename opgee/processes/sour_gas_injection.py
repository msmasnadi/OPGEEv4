#
# SourGasInjection class
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


class SourGasInjection(Process):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "gas",
        ]

        self._required_outputs = [
            "gas for gas partition",
        ]

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # mass rate
        input = self.find_input_stream("gas")
        if input.is_uninitialized():
            return

        loss_rate = self.get_compressor_and_well_loss_rate(input)
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        gas_to_partition = self.find_output_stream("gas for gas partition")
        gas_to_partition.copy_flow_rates_from(input)
        gas_to_partition.subtract_rates_from(gas_fugitives)

        self.set_iteration_value(gas_to_partition.total_flow_rate())

        field.save_process_data(is_input_from_well=True)

        # emissions
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
