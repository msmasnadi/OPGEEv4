#
# PreMembraneCompressor class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..emissions import EM_FUGITIVES
from ..log import getLogger
from ..process import Process
from ..processes.compressor import Compressor
from ..units import ureg
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class PreMembraneCompressor(Process):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "gas",
        ]

        self._required_outputs = [
            "gas",
        ]

        self.discharge_press = None
        self.eta_compressor = None
        self.prime_mover_type = None
        self.cache_attributes()

    def cache_attributes(self):
        self.discharge_press = self.attr("discharge_press")
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas")
        if input.is_uninitialized():
            return

        loss_rate = self.get_compressor_and_well_loss_rate(input)
        loss_rate = min(ureg.Quantity(0.95, "frac"), loss_rate)
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        gas_to_CO2_membrane = self.find_output_stream("gas")
        gas_to_CO2_membrane.copy_flow_rates_from(input)
        gas_to_CO2_membrane.subtract_rates_from(gas_fugitives)
        self.set_iteration_value(gas_to_CO2_membrane.total_flow_rate())

        overall_compression_ratio = self.discharge_press / input.tp.P
        energy_consumption, output_temp, output_press = \
            Compressor.get_compressor_energy_consumption(
                self.field,
                self.prime_mover_type,
                self.eta_compressor,
                overall_compression_ratio,
                input)

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption)

        # import/export
        self.set_import_from_energy(energy_use)

        # emissions
        self.set_combustion_emissions()
        self.emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
