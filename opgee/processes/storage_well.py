from ..core import STP
from ..emissions import EM_FUGITIVES
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class StorageWell(Process):
    """
    Storage well calculate fugitive emission from storage wells.

    """

    def _after_init(self):
        super()._after_init()
        self.loss_rate = self.venting_fugitive_rate()

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas for well")

        if input.is_uninitialized():
            return

        gas_fugitives_temp = self.set_gas_fugitives(input, self.loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp, tp=STP)

        gas_to_separator = self.find_output_stream("gas for separator")
        gas_to_separator.copy_gas_rates_from(input)
        gas_to_separator.subtract_gas_rates_from(gas_fugitives)

        # emissions
        emissions = self.emissions
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
