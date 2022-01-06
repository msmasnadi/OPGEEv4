from opgee.stream import Stream
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class StorageSeparator(Process):
    """
    Storage well calculate fugitive emission from storage wells.

    """

    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.water_production_frac = self.attr("water_production_frac")
        self.outlet_temp = self.attr("outlet_temp")
        self.outlet_press = self.attr("outlet_press")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas for separator")

        if input.is_empty():
            return

        # produced water stream
        prod_water = Stream("produced water stream", temperature=self.outlet_temp, pressure=self.outlet_press)
        prod_water.set_liquid_flow_rate("H2O", (input.total_gas_rate() * self.water_production_frac).m)

        gas_to_compressor = self.find_output_stream("gas for storage")
        gas_to_compressor.copy_gas_rates_from(input)
        gas_to_compressor.set_temperature_and_pressure(temp=self.outlet_temp, press=self.outlet_press)

        #TODO: Future versions of OPGEE may treat this process in more detail.




