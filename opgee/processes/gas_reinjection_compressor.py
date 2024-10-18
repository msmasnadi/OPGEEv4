#
# GasReinjectionCompressor class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .. import ureg
from ..emissions import EM_FUGITIVES
from ..energy import EN_ELECTRICITY
from ..log import getLogger
from ..process import Process
from .compressor import Compressor
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class GasReinjectionCompressor(Process):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "gas for gas reinjection compressor"
        ]

        self._required_outputs = [
            "gas for gas reinjection well"
        ]

        self.air_separation_energy_intensity = None
        self.eta_compressor = None
        self.flood_gas_type = None
        self.gas_flooding = None
        self.natural_gas_reinjection = None
        self.prime_mover_type = None
        self.res_press = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        self.res_press = field.res_press
        self.prime_mover_type = self.attr("prime_mover_type")
        self.eta_compressor = self.attr("eta_compressor")
        self.natural_gas_reinjection = field.natural_gas_reinjection
        self.gas_flooding = field.gas_flooding
        self.flood_gas_type = field.flood_gas_type
        self.air_separation_energy_intensity = self.attr("air_separation_energy_intensity")

    def check_enabled(self):
        if not self.natural_gas_reinjection and not self.gas_flooding:
            self.set_enabled(False)

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        # TODO: unclear how this can work if the input stream doesn't exist
        input = self.find_input_stream("gas for gas reinjection compressor", raiseError=False)

        if input is None or input.is_uninitialized():
            return

        loss_rate = self.get_compressor_and_well_loss_rate(input)
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        gas_to_well = self.find_output_stream("gas for gas reinjection well")
        gas_to_well.copy_flow_rates_from(input)
        gas_to_well.subtract_rates_from(gas_fugitives)

        discharge_press = self.res_press + ureg.Quantity(500., "psi")
        overall_compression_ratio = discharge_press / input.tp.P
        energy_consumption, output_temp, _ = Compressor.get_compressor_energy_consumption(
            self.field,
            self.prime_mover_type,
            self.eta_compressor,
            overall_compression_ratio,
            input)

        gas_to_well.tp.set(T=output_temp, P=discharge_press)

        self.set_iteration_value(gas_to_well.total_flow_rate())

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption)

        if field.get_process_data("N2_reinjection_volume_rate"):
            N2_volume_rate = field.get_process_data("N2_reinjection_volume_rate")
            energy_consump_air_separation = N2_volume_rate * self.air_separation_energy_intensity
            energy_use.set_rate(EN_ELECTRICITY, energy_consump_air_separation)


        # import/export
        self.set_import_from_energy(energy_use)

        # emissions
        self.set_combustion_emissions()
        self.emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
