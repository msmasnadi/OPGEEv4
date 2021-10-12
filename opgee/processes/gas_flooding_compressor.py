from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class GasFloodingCompressor(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.flood_gas_type = field.attr("flood_gas_type")
        self.oil_prod = field.attr("oil_prod")
        self.GFIR = field.attr("GFIR")
        self.gas_flooding = field.attr("gas_flooding")
        self.offset_gas_comp = self.attrs_with_prefix("offset_gas_comp_")
        self.gas_flooding_vol_rate = self.oil_prod * self.GFIR
        self.frac_CO2_breakthrough = field.attr("frac_CO2_breakthrough")

    def run(self, analysis):
        self.print_running_msg()

        if self.gas_flooding != 1:
            return

        # mass rate
        # imported gas flooding stream is empty stream
        input = self.find_input_stream("gas for gas flooding")



