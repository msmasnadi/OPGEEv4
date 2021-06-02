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
        output = self.find_output_stream("crude oil")
        gas_fugitives = self.set_gas_fugitives(output)

        input = self.find_input_stream("crude oil")
        input.add_flow_rates_from(output)
        input.add_flow_rates_from(gas_fugitives)
