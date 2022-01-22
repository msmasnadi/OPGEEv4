from ..emissions import EM_FUGITIVES
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class GasGathering(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")

    def run(self, analysis):
        self.print_running_msg()

        if not self.all_streams_ready("gas for gas gathering"):
            return

        # mass_rate
        input = self.find_input_streams("gas for gas gathering", combine=True)

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp, temp=self.std_temp, press=self.std_press)

        gas_to_dehydration = self.find_output_stream("gas")
        gas_to_dehydration.copy_flow_rates_from(input)
        gas_to_dehydration.subtract_gas_rates_from(gas_fugitives)

        # emissions
        emissions = self.emissions
        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)

