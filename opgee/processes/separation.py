from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class Separation(Process):
    def run(self, analysis):
        self.print_running_msg()

    def impute(self):
        field = self.get_field()

        oil_after = field.find_stream("oil after separator")
        water_after = field.find_stream("water after separator")
        gas_after = field.find_stream("gas after separator")
        gas_fugitives = field.find_stream("gas fugitives from separator")

        oil_before = field.find_stream("oil before separator")
        water_before = field.find_stream("water before separator")
        gas_before = field.find_stream("gas before separator")

        downhole_pump = field.find_process("DownholePump")
        wellhead_temp = downhole_pump.attr("wellhead_temperature")
        wellhead_press = downhole_pump.attr("wellhead_pressure")
        for stream in [oil_before, water_before, gas_before]:
            stream.set_temperature_and_pressure(wellhead_temp, wellhead_press)

        oil_before.copy_flow_rates_from(oil_after)
        water_before.copy_flow_rates_from(water_after)
        gas_before.copy_flow_rates_from(gas_after)
        gas_before.add_flow_rates_from(gas_fugitives)