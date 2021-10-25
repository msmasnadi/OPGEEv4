from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID
from ..emissions import Emissions, EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class CO2InjectionWell(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_stream("gas for CO2 injection well")

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

        gas_to_reservoir = self.find_output_stream("gas for reservoir")
        gas_to_reservoir.copy_flow_rates_from(input)
        gas_to_reservoir.subtract_gas_rates_from(gas_fugitives)
        gas_to_reservoir.set_temperature_and_pressure(input.temperature, input.pressure)

        # emissions
        emissions = self.emissions
        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)
