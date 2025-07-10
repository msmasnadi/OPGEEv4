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
from ..combine_streams import combine_streams
from ..core import TemperaturePressure
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
            "gas",
            "iteration gas"
        ]

        self._required_outputs = [
            "H2",
            "gas"
        ]

        self.model = self.field.model
        self.efficiency = 0.40 # TODO add an attribute

        # Initialize other necessary attributes.
        self.cache_attributes()

    def cache_attributes(self):
        """
        Cache attributes or calculations needed for the process.
        """
        self.slip_rate = self.field.attr("slip_rate")
        self.waste_P = self.field.attr("PSA_waste_gas_P")
        self.waste_T = self.field.attr("PSA_waste_gas_T")

    def run(self, analysis):
        """
        Execute the process simulation.

        Args:
            analysis: The analysis context for running the simulation.
        
        Returns:
            None
        """
        self.print_running_msg()

        gas_in = self.find_input_stream("gas")

        H2_in = self.find_output_stream("H2")
        H2_in.set_gas_flow_rate("H2", gas_in.gas_flow_rate("H2") * (1-self.slip_rate))
        waste_gas_in = self.find_output_stream("gas")
        tp = TemperaturePressure(self.waste_T, self.waste_P)
        waste_gas_in.copy_gas_rates_from(gas_in, tp = tp) # TODO: the TP of waste stream should change based on the exiting P from PSA
        waste_gas_in.subtract_rates_from(H2_in)

        # step 1 calculate how much total electricity we actually need from all processes
        energy_list = [proc.energy.get_rate("Electricity") for proc in self.field.processes() if proc != self]
        required_energy = sum(energy_list)

        # step 2 calculate the energy density of the current gas stream
        # step 3 calculate how much electricity can be generated from the current gas stream
        energy_flow_rate_from_waste = self.energy_rates(waste_gas_in)
        electricity_rate_from_waste = energy_flow_rate_from_waste * self.efficiency # mmbtu/day

        # record emissions
        emissions = self.emissions
        emission_stream = Stream("emission_stream", tp=waste_gas_in.tp)

        # burn waste gas first
        percentage_waste_gas_burned = required_energy/electricity_rate_from_waste
        self.field.save_process_data(percentage_waste_gas_burned=percentage_waste_gas_burned)

        emission_stream.add_combustion_CO2_from(waste_gas_in, (percentage_waste_gas_burned if percentage_waste_gas_burned < 1 else 1))

        waste_gas_in.multiply_flow_rates(1 - (percentage_waste_gas_burned if percentage_waste_gas_burned < 1 else 1))

        # check if waste gas was sufficient
        remaining_energy_needed = required_energy - electricity_rate_from_waste *(percentage_waste_gas_burned if percentage_waste_gas_burned < 1 else 1)

        percentage_H2_burned = 0
        if remaining_energy_needed > 0:
            energy_flow_rate_from_H2 = self.energy_rates(H2_in)
            electricity_rate_from_H2 = energy_flow_rate_from_H2 * self.efficiency  # mmbtu/day
            percentage_H2_burned = remaining_energy_needed / electricity_rate_from_H2
            em2 = Stream("emission_stream2", tp=H2_in.tp)
            em2.add_combustion_CO2_from(H2_in, (
                percentage_H2_burned if percentage_H2_burned < 1 else 1))
            emission_stream = combine_streams([emission_stream, em2])

        self.field.save_process_data(percentage_H2_burned=percentage_H2_burned)
        H2_in.multiply_flow_rates(1-(percentage_H2_burned if percentage_H2_burned < 1 else 1))

        emissions.set_from_stream(EM_COMBUSTION, emission_stream)

        # # step 5 record energy used
        # # TODO: this is commented out bcuz we are producing energy
        # # not generating energy
        # # the required energy amount is documented at each energy-consuming process
        # energy_use = self.energy
        # energy_use.set_rate(EN_ELECTRICITY, required_energy)

        self.set_iteration_value(required_energy)

        self.set_embodied_emissions()

    def energy_rates(self, input):
        return self.field.gas.energy_flow_rate(input)


