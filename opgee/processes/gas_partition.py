from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID
from opgee.stream import Stream

_logger = getLogger(__name__)


class GasPartition(Process):
    """
    Gas partition is to check the reasonable amount of gas goes to gas lifting and gas reinjection

    """
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.gas_lifting = field.attr("gas_lifting")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_streams("gas for gas partition", combine=True)

        gas_lifting = self.find_output_stream("gas lifting")
        if self.gas_lifting == 1:
            if gas_lifting.temperature.m == 0.0 or gas_lifting.pressure.m == 0.0:
                gas_lifting = self.field.get_process_data("gas_lifting_stream")

        # Check
        # self.set_iteration_value(output.total_flow_rate())
        def test_diff(input, output, name):
            diff = output.gas_flow_rate(name) - input.gas_flow_rate(name)
            return diff if diff.m >= 0 else 0

        self.set_iteration_value([test_diff(input, gas_lifting, name) for name in Stream.emission_composition])

        # self.
