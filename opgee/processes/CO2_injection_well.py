#
# CO2InjectionWell class
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


class CO2InjectionWell(Process):
    def _after_init(self):
        super()._after_init()

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_stream("gas for CO2 injection well")
        if input.is_uninitialized():
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        gas_to_reservoir = self.find_output_stream("gas for reservoir")
        gas_to_reservoir.copy_flow_rates_from(input)
        gas_to_reservoir.subtract_rates_from(gas_fugitives)

        # emissions
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
