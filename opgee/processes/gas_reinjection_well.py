#
# GasReinjectionWell class
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


class GasReinjectionWell(Process):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "gas"
        ]

        self._required_outputs = [
            "gas",
        ]

        self.gas_flooding = None
        self.natural_gas_reinjection = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        self.gas_flooding = field.gas_flooding
        self.natural_gas_reinjection = field.natural_gas_reinjection

    def check_enabled(self):
        if not self.natural_gas_reinjection and not self.gas_flooding:
            self.set_enabled(False)

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_stream("gas")

        if input.is_uninitialized():
            return

        loss_rate = self.get_compressor_and_well_loss_rate(input)
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        gas_to_reservoir = self.find_output_stream("gas")
        gas_to_reservoir.copy_flow_rates_from(input)
        gas_to_reservoir.subtract_rates_from(gas_fugitives)

        self.set_iteration_value(gas_to_reservoir.total_flow_rate())

        # emissions
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
