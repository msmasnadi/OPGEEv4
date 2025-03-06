#
# NewProcess class
#
# Author: Spencer Zhihao Zhang
#
# Copyright (c) [2025] [Stanford University].
# See LICENSE.txt for license details.
#

import numpy as np
from openpyxl.styles.builtins import output

from .shared import get_energy_consumption
from ..emissions import EM_COMBUSTION
from ..units import ureg
from ..error import OpgeeException
from ..log import getLogger
from ..process import Process
from ..stream import Stream
from ..thermodynamics import Gas
from ..energy import EN_ELECTRICITY

_logger = getLogger(__name__)


class OnsiteElectricityGeneration(Process):
    """
    A class to convert an input gas stream into electricity based on given efficiency and composition,
    and to record the resulting emissions.
    """

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # Declare required inputs/outputs.
        self._required_inputs = [
            # Add required inputs here, e.g., "input stream"
            "gas for electricity generation" # assume only fuel gas comes in, not considering oil
        ]
        self._required_outputs = [
            "gas" # default goes to PSA
            # Add required outputs here, e.g., "output stream"
        ]

        self.model = self.field.model
        self.efficiency = 0.40 # TODO add an attribute

        # Initialize other necessary attributes.
        self.cache_attributes()

    def cache_attributes(self):
        """
        Cache attributes or calculations needed for the process.
        """
        pass

    def run(self, analysis):
        """
        Execute the process simulation.

        Args:
            analysis: The analysis context for running the simulation.
        
        Returns:
            None
        """
        input = self.find_input_stream("gas for electricity generation")

        # step 1 calculate how much total electricity we actually need from all processes
        required_energy = sum([proc.energy.get_rate("Electricity") for proc in self.field.processes()])

        # step 2 calculate the energy density of the current gas stream
        # step 3 calculate how much electricity can be generated from the current gas stream
        energy_flow_rate = self.energy_rates(input)
        electricity_rate = energy_flow_rate * self.efficiency # mmbtu/day

        # step calculate what percentage of the incoming gas stream would be burnt for electricity
        # step subtract the gas amount for electricity generation / save the rest for output
        percentage_gas_for_electricity = required_energy/electricity_rate
        output = self.find_output_stream("gas")
        output.copy_gas_rates_from(input)
        output.multiply_flow_rates(1-percentage_gas_for_electricity)

        # step 2 calculate the emission factor (gCO2e/MJ) of the gas
        # step 4 record emissions
        # modified from flaring.py
        emissions = self.emissions
        emission_stream = Stream("emission_stream", tp=input.tp)
        emission_stream.add_combustion_CO2_from(input, percentage_gas_for_electricity)
        emissions.set_from_stream(EM_COMBUSTION, emission_stream)

        # step 5 record energy used
        energy_use = self.energy
        energy_use.set_rate(EN_ELECTRICITY, required_energy)

    def energy_rates(self, input):
        return self.field.gas.energy_flow_rate(input)


