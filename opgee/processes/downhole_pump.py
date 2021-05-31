from ..error import OpgeeException
from ..process import Process
from ..log import getLogger
from opgee.stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID


_logger = getLogger(__name__)


class DownholePump(Process):
    def run(self, analysis):
        self.print_running_msg()

        # lift_gas = self.find_input_streams('lifting gas', combine=True, raiseError=False)


    def impute(self):
        # TBD: copy some output streams to input streams, and
        # TBD: sum rates of some substances from outputs to compute input rates
        field = self.get_field()

        res_temp = field.attr("res_temp")

        output = self.find_output_stream("crude oil")
        gas_at_wellbore = Stream("gas_at_wellbore", temperature=output.temperature, pressure=output.pressure)
        gas_at_wellbore.copy_gas_rates_from(output)
        gas_fugitives = self.set_gas_fugitives(gas_at_wellbore, "gas fugitives from downhole pump")
        output.add_flow_rates_from(gas_fugitives)

        input = self.find_input_stream("crude oil")
        #input.set_temperature_and_pressure(res_temp, wellhead_press)
        input.add_flow_rates_from(output)
