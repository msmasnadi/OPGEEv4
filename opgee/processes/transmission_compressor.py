import math

from opgee.stream import Stream
from .shared import get_energy_carrier
from ..compressor import Compressor
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class TransmissionCompressor(Process):
    """
    Transmission compressor calculate compressor emissions after the production site boundary.

    """

    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.press_drop_per_dist = self.attr("press_drop_per_dist")
        self.transmission_dist = self.attr("transmission_dist")
        self.transmission_freq = self.attr("transmission_freq")
        self.transmission_inlet_press = self.attr("transmission_inlet_press")
        self.prime_mover_type = self.attr("prime_mover_type")
        self.eta_compressor = self.attr("eta_compressor")
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.gas_to_storage_frac = self.attr("gas_to_storage_frac")
        self.natural_gas_to_liquefaction_frac = field.attr("natural_gas_to_liquefaction_frac")
        self.transmission_sys_discharge = self.attr("transmission_sys_discharge")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas")

        if input.is_uninitialized():
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

        input_energy_flow_rate = self.field.gas.energy_flow_rate(input)

        # Transmission system properties
        station_outlet_press = self.press_drop_per_dist * self.transmission_freq + self.transmission_inlet_press
        num_compressor_stations = math.ceil(self.transmission_dist / self.transmission_freq)

        # initial compressor properties
        overall_compression_ratio_init = station_outlet_press / input.pressure
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

        gas_consumption_frac = energy_use.get_rate(energy_carrier) / input_energy_flow_rate
        fuel_gas_stream = Stream("fuel gas stream", temperature=input.temperature, pressure=input.pressure)
        fuel_gas_stream.copy_gas_rates_from(input)
        fuel_gas_stream.multiply_flow_rates(gas_consumption_frac.m)

        gas_to_storage = self.find_output_stream("gas for storage")
        gas_to_storage.copy_gas_rates_from(input)
        gas_to_storage.subtract_gas_rates_from(fuel_gas_stream)
        gas_to_storage.subtract_gas_rates_from(gas_fugitives)
        gas_to_storage.multiply_flow_rates(self.gas_to_storage_frac.m)
        gas_to_storage.set_temperature_and_pressure(temp=output_temp_init, press=output_press_init)

        gas_to_liquefaction = self.find_output_stream("LNG")
        gas_to_liquefaction.copy_gas_rates_from(input)
        gas_to_liquefaction.subtract_gas_rates_from(fuel_gas_stream)
        gas_to_liquefaction.subtract_gas_rates_from(gas_fugitives)
        gas_to_liquefaction.multiply_flow_rates(self.natural_gas_to_liquefaction_frac.m)
        gas_to_liquefaction.set_temperature_and_pressure(temp=output_temp_init, press=self.transmission_sys_discharge)

        gas_to_distribution = self.find_output_stream("gas for distribution")
        gas_to_distribution.copy_gas_rates_from(input)
        gas_to_distribution.subtract_gas_rates_from(fuel_gas_stream)
        gas_to_distribution.subtract_gas_rates_from(gas_fugitives)
        gas_to_distribution.subtract_gas_rates_from(gas_to_storage)
        gas_to_distribution.subtract_gas_rates_from(gas_to_liquefaction)
        gas_to_distribution.set_temperature_and_pressure(temp=output_temp_init, press=self.transmission_sys_discharge)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combustion_emission)
        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)
