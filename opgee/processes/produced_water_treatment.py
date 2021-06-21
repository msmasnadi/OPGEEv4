from ..log import getLogger
from ..process import Process
from ..stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID
from opgee import ureg

_logger = getLogger(__name__)


class ProducedWaterTreatment(Process):
    def run(self, analysis):
        self.print_running_msg()

        field = self.get_field()
        std_temp = field.model.const("std-temperature")
        std_press = field.model.const("std-pressure")
        water_treatment_table = self.model.water_treatment

        # mass rate
        input = self.find_input_streams("water", combine=True)
        total_water_mass_rate = input.liquid_flow_rate("H2O")

        output_steam = self.find_output_stream("water for steam", raiseError=False)
        output_reinjection = self.find_output_stream("water for reinjection")
        output_surface_disposal = self.find_output_stream("water for surface disposal")
        output_subsurface_disposal = self.find_output_stream("water for subsurface disposal")
        # output.set_liquid_flow_rate("H2O", total_water_mass_rate)
        output_subsurface_disposal.set_temperature_and_pressure(input.temperature, input.pressure)
        output_steam.set_temperature_and_pressure(input.temperature, input.pressure)
        output_reinjection.set_temperature_and_pressure(input.temperature, input.pressure)
        output_surface_disposal.set_temperature_and_pressure(std_temp, std_press)


