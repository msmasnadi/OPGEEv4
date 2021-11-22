from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class GasProductionSiteBoundary(Process):
    """
    Gas production site boundary is to collect exported gas from gas branch to the first gas process boundary

    """

    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas_boundary = field.attr("gas_boundary")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas for production site boundary")

        if self.gas_boundary == "Production site boundary" or input.is_empty():
            return

        output = self.find_output_stream("gas for transmission compressor")
        output.copy_flow_rates_from(input)
        output.set_temperature_and_pressure(input.temperature, input.pressure)
