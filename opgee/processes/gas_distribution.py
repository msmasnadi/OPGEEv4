from ..emissions import EM_FUGITIVES
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class GasDistribution(Process):
    """
    Gas distribution calculates emission of gas to distribution

    """
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.frac_loss =\
            self.attr("frac_loss_distribution") + self.attr("frac_loss_meter") + self.attr("frac_loss_enduse")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        input = self.find_input_streams("gas for distribution", combine=True)

        if input.is_uninitialized():
            return

        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(input, tp=field.stp)
        gas_fugitives.multiply_flow_rates(self.frac_loss.m)

        gas_to_customer = self.find_output_stream("gas")
        gas_to_customer.copy_flow_rates_from(input)
        gas_to_customer.subtract_gas_rates_from(gas_fugitives)

        # emissions
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)





