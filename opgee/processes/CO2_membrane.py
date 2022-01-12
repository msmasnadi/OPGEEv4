from ..log import getLogger
from ..process import Process
from ..stream import PHASE_GAS

_logger = getLogger(__name__)


class CO2Membrane(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.membrane_comp = field.attrs_with_prefix("membrane_separation_comp_")
        self.feed_press_AGR = field.attr("feed_press_AGR")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas for CO2 membrane")

        gas_to_AGR = self.find_output_stream("gas for AGR")
        AGR_mol_fracs = 1 - self.membrane_comp
        gas_to_AGR.copy_flow_rates_from(input)
        gas_to_AGR.multiply_factor_from_series(AGR_mol_fracs, PHASE_GAS)
        gas_to_AGR.set_temperature_and_pressure(self.std_temp, self.feed_press_AGR)

        gas_to_compressor = self.find_output_stream("gas for CO2 compressor")
        gas_to_compressor.copy_flow_rates_from(input)
        gas_to_compressor.multiply_factor_from_series(self.membrane_comp, PHASE_GAS)
        gas_to_compressor.set_temperature_and_pressure(self.std_temp, input.pressure * 0.33)
