from ..stream import Stream
from ..compressor import Compressor
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class LNGTransport(Process):
    """
    LNG transport calculate emissions from LNG to the market

    """
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.ocean_tank_size = field.attr("ocean_tanker_size")
        # self.LNG_transport_shared_fuel = field.model.LNG_transport_share_fuel


    def run(self, analysis):
        self.print_running_msg()

        # input = self.find_input_stream("gas for transport")
        #
        # if input.is_uninitialized():
        #     return




