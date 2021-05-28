from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class DownholePump(Process):
    def run(self, analysis):
        self.print_running_msg()

    def impute(self):
        # TBD: copy some output streams to input streams, and
        # TBD: sum rates of some substances from outputs to compute input rates
        field = self.get_field()

        output = self.find_output_streams("crude oil")
        gas_fugitives = self.find_stream("gas fugitives from downhole pump")

        input = self.find_input_streams("crude oil")
        input.set_temperature_and_pressure(wellhead_temp, wellhead_press)
        input.add_flow_rates_from(output)
