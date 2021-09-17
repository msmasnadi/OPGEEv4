from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID
from opgee import ureg
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY
from ..emissions import Emissions, EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class PreMembraneChiller(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.outlet_temp = field.attr("chiller_outlet_temp")
        self.fug_emissions_chiller = field.attr("fug_emissions_chiller")
        self.pressure_drop = ureg.Quantity(56, "delta_degC")
        self.feed_stream_mass_rate = ureg.Quantity(6.111072, "tonne/day")
        self.compressor_load = ureg.Quantity(3.44, "MW")
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_stream("gas for chiller")

        gas_fugitives_temp = self.set_gas_fugitives(input, self.fug_emissions_chiller.to("frac"))
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

        gas_to_compressor = self.find_output_stream("gas for compressor")
        gas_to_compressor.copy_flow_rates_from(input)
        gas_to_compressor.subtract_gas_rates_from(gas_fugitives)
        gas_to_compressor.set_temperature_and_pressure(self.outlet_temp, input.pressure)

        delta_temp = input.temperature - self.outlet_temp
        energy_consumption = (self.compressor_load * input.total_gas_rate() /
                              self.feed_stream_mass_rate * delta_temp / self.pressure_drop)

        # energy-use
        energy_use = self.energy
        energy_use.set_rate(EN_ELECTRICITY, energy_consumption)

        # emissions
        emissions = self.emissions
        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)





