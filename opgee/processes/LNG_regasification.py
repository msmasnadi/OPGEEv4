#
# LNGRegasification class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .shared import get_energy_carrier, get_energy_consumption
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class LNGRegasification(Process):
    """
    LNG liquefaction calculate emission of transported gas to regasification
    """
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self._required_inputs = [
            "gas",
        ]

        # TODO: avoid process names in contents.
        self._required_outputs = [
            "gas for distribution",
        ]

        self.cache_attributes()

    def cache_attributes(self):
        self.efficiency = self.attr("efficiency")
        self.energy_intensity_regas = self.attr("energy_intensity_regas")
        self.prime_mover_type = self.attr("prime_mover_type")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas")

        if input.is_uninitialized():
            return

        gas_mass_rate = input.total_gas_rate()
        gas_mass_energy_density = self.gas.mass_energy_density(input)
        gas_LHV_rate = gas_mass_rate * gas_mass_energy_density
        total_regasification_requirement = self.energy_intensity_regas * gas_LHV_rate

        energy_consumption = get_energy_consumption(self.prime_mover_type, total_regasification_requirement)
        gas_to_distribution = self.find_output_stream("gas for distribution")
        gas_to_distribution.copy_flow_rates_from(input)

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption)

        # import/export
        self.set_import_from_energy(energy_use)

        # emissions
        self.set_combustion_emissions()







