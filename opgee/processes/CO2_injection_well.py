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
    """
        This process models a injection well used for injecting CO2 into the reservoir.

        input streams:
            - gas for CO2 injection well: gas stream with CO2 for injection

        output streams:
            - gas for reservoir: gas stream with CO2 injected into reservoir
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

    def run(self, analysis):
        self.print_running_msg()

        # Get input stream and check if it's initialized
        input = self.find_input_stream("gas for CO2 injection well")
        if input.is_uninitialized():
            return

        # Calculate fugitive loss rate
        loss_rate = self.get_compressor_and_well_loss_rate(input)

        # Set up gas fugitives stream and calculate flow rates
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        # Set up output gas stream for reservoir injection
        gas_to_reservoir = self.find_output_stream("gas for reservoir")

        # Copy flow rates from input gas stream to output gas stream
        gas_to_reservoir.copy_flow_rates_from(input)

        # Subtract fugitive flow rates from input gas stream
        gas_to_reservoir.subtract_rates_from(gas_fugitives)

        # Set fugitive emissions rates
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
