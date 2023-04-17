#
# CO2InjectionWell class
#
# Author: Richard Plevin and Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..constants import std_pressure
from ..emissions import EM_COMBUSTION
from ..log import getLogger
from ..process import Process
from ..processes.compressor import Compressor
from ..stream import PHASE_GAS
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class CO2Membrane(Process):
    """
    This process represents the separation of CO2 from natural gas using a membrane.

    input streams:
        - gas for CO2 membrane

    output streams:
        - gas for AGR
        - gas for CO2 compressor

    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        field = self.field
        self.gas = field.gas
        self.membrane_comp = field.imported_gas_comp["Membrane Separation Gas"]
        self.press_drop = self.attr("press_drop_across_membrane")
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")
        self.AGR_feedin_press = field.AGR_feedin_press

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        input = self.find_input_stream("gas for CO2 membrane")
        if input.is_uninitialized():
            return

        gas_to_AGR = self.find_output_stream("gas for AGR")
        AGR_mol_fracs = 1 - self.membrane_comp
        gas_to_AGR.copy_flow_rates_from(input)
        gas_to_AGR.tp.P = self.AGR_feedin_press
        gas_to_AGR.tp.T = field.stp.T
        gas_to_AGR.multiply_factor_from_series(AGR_mol_fracs, PHASE_GAS)

        gas_to_compressor = self.find_output_stream("gas for CO2 compressor")
        gas_to_compressor.copy_flow_rates_from(input)
        gas_to_compressor.tp.set(T=field.stp.T, P=input.tp.P * 0.33)
        gas_to_compressor.multiply_factor_from_series(self.membrane_comp, PHASE_GAS)

        inlet_pressure_after_membrane = max(std_pressure, input.tp.P - self.press_drop)
        discharge_press = input.tp.P
        overall_compression_ratio = discharge_press / inlet_pressure_after_membrane
        energy_consumption, temp, _ = Compressor.get_compressor_energy_consumption(field,
                                                                                   self.prime_mover_type,
                                                                                   self.eta_compressor,
                                                                                   overall_compression_ratio,
                                                                                   input)

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)
