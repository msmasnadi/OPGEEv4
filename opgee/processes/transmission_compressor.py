#
# TransmissionCompressor class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import math

from .compressor import Compressor
from .shared import get_energy_carrier
from ..core import TemperaturePressure
from ..emissions import EM_FUGITIVES
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)

class TransmissionCompressor(Process):
    """
    Transmission compressor calculate compressor emissions after the production site boundary.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.eta_compressor = None
        self.gas_to_storage_frac = None
        self.loss_rate = None
        self.natural_gas_to_liquefaction_frac = None
        self.press_drop_per_dist = None
        self.prime_mover_type = None
        self.transmission_dist = None
        self.transmission_freq = None
        self.transmission_inlet_press = None
        self.transmission_sys_discharge = None

        self.cache_attributes()

    def cache_attributes(self):
        self.press_drop_per_dist = self.attr("press_drop_per_dist")
        self.transmission_dist = self.attr("transmission_dist")
        self.transmission_freq = self.attr("transmission_freq")
        self.transmission_inlet_press = self.attr("transmission_inlet_press")
        self.prime_mover_type = self.attr("prime_mover_type")
        self.eta_compressor = self.attr("eta_compressor")
        self.gas_to_storage_frac = self.attr("gas_to_storage_frac")
        self.natural_gas_to_liquefaction_frac = self.field.natural_gas_to_liquefaction_frac
        self.transmission_sys_discharge = self.attr("transmission_sys_discharge")
        self.loss_rate = self.venting_fugitive_rate()

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas")

        if input.is_uninitialized():
            return

        gas_fugitives = self.set_gas_fugitives(input, self.loss_rate)

        # Transmission system properties
        station_outlet_press = self.press_drop_per_dist * self.transmission_freq + self.transmission_inlet_press
        num_compressor_stations = math.ceil(self.transmission_dist / self.transmission_freq)

        # initial compressor properties
        overall_compression_ratio_init = station_outlet_press / input.tp.P
        energy_consumption_init, output_temp_init, output_press_init = \
            Compressor.get_compressor_energy_consumption(
                self.field,
                self.prime_mover_type,
                self.eta_compressor,
                overall_compression_ratio_init,
                input)

        # Along-pipeline booster compressor properties
        overall_compression_ratio_booster = station_outlet_press / self.transmission_inlet_press
        energy_consumption_booster, output_temp_booster, output_press_booster = \
            Compressor.get_compressor_energy_consumption(
                self.field,
                self.prime_mover_type,
                self.eta_compressor,
                overall_compression_ratio_booster,
                input)

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption_init +
                            energy_consumption_booster * num_compressor_stations)

        # import/export
        self.set_import_from_energy(energy_use)

        gas_to_storage = self.find_output_stream("gas for storage")
        gas_to_storage.copy_gas_rates_from(input, tp=TemperaturePressure(output_temp_init, output_press_init))
        gas_to_storage.subtract_rates_from(gas_fugitives)
        gas_to_storage.multiply_flow_rates(self.gas_to_storage_frac.m)

        gas_tp = TemperaturePressure(output_temp_init, self.transmission_sys_discharge)
        gas_to_liquefaction = self.find_output_stream("LNG")
        gas_to_liquefaction.copy_gas_rates_from(input, tp=gas_tp)
        gas_to_liquefaction.subtract_rates_from(gas_fugitives)
        gas_to_liquefaction.multiply_flow_rates(self.natural_gas_to_liquefaction_frac.m)

        gas_to_distribution = self.find_output_stream("gas for distribution")
        gas_to_distribution.copy_gas_rates_from(input, tp=gas_tp)
        gas_to_distribution.subtract_rates_from(gas_fugitives)
        gas_to_distribution.subtract_rates_from(gas_to_storage)
        gas_to_distribution.subtract_rates_from(gas_to_liquefaction)

        # emissions
        self.set_combustion_emissions()
        self.emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
