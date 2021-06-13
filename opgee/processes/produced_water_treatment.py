from ..log import getLogger
from ..process import Process
from ..stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID
from opgee import ureg

_logger = getLogger(__name__)


def get_final_temperature(streams):
    """
    T = (m1T1 + m2T2 ) / ( m1 + m2 )


    :param streams:
    :return: (float) final temperature of produced water treatment process
    """
    total_mass = ureg.Quantity(0, "tonne/day")
    total_mass_temp = ureg.Quantity(0, "tonne*kelvin/day")

    for name in streams:
        stream = streams[name]
        total_mass += stream.flow_rate("H2O", PHASE_LIQUID)
        total_mass_temp += stream.flow_rate("H2O", PHASE_LIQUID) * stream.temperature.to("kelvin")
    result = total_mass_temp / total_mass
    return result.to("degF")


class ProducedWaterTreatment(Process):
    def run(self, analysis):
        self.print_running_msg()

        field = self.get_field()

        # mass rate
        input = self.find_input_streams("water", combine=True)
        total_water_mass_rate = input.liquid_flow_rate("H2O")

        treatment_temp = get_final_temperature(input)
        treatment_press = input["separator to produced water treatment"].pressure

        output = self.find_output_stream("water")
        output.set_liquid_flow_rate("H2O", total_water_mass_rate)
        output.set_temperature_and_pressure(treatment_temp, treatment_press)
