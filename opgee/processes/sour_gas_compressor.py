#
# SourGasCompressor class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .. import ureg
from ..emissions import EM_FUGITIVES
from ..log import getLogger
from ..process import Process
from ..processes.compressor import Compressor
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class SourGasCompressor(Process):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "gas for sour gas compressor",
        ]

        self._required_outputs = [
            "gas",
        ]

        self.eta_compressor = None
        self.prime_mover_type = None
        self.res_press = None

        self.cache_attributes()

    def cache_attributes(self):
        self.res_press = self.field.res_press
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # mass rate
        input = self.find_input_stream("gas for sour gas compressor")
        if input.is_uninitialized():
            return

        loss_rate = self.get_compressor_and_well_loss_rate(input)
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        gas_to_injection = self.find_output_stream("gas")
        gas_to_injection.copy_flow_rates_from(input)
        gas_to_injection.subtract_rates_from(gas_fugitives)

        discharge_press = self.res_press + ureg.Quantity(500.0, "psia")
        overall_compression_ratio = discharge_press / input.tp.P
        energy_consumption, output_temp, _ = \
            Compressor.get_compressor_energy_consumption(
                self.field,
                self.prime_mover_type,
                self.eta_compressor,
                overall_compression_ratio,
                input)

        gas_to_injection.tp.set(T=output_temp, P=discharge_press)
        field.save_process_data(sour_gas_reinjection_mass_rate=gas_to_injection.gas_flow_rate("CO2"))

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption)

        # import/export
        self.set_import_from_energy(energy_use)

        # emissions
        self.set_combustion_emissions()
        self.emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)



