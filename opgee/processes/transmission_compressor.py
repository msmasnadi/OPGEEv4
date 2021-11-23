from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID, PHASE_GAS
from opgee.stream import Stream
from ..config import getParam
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from .. import ureg

_logger = getLogger(__name__)


class TransmissionCompressor(Process):
    """
    Transmission compressor calculate compressor emissions after the production site boundary

    """

    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        # self.gas_boundary = field.attr("gas_boundary")
        self.press_drop_per_dist = self.attr("press_drop_per_dist")
        self.transmission_dist = self.attr("transmission_dist")
        self.transmission_freq = self.attr("transmission_freq")
        self.transmission_inlet_press = self.attr("transmission_inlet_press")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas")

        # if self.gas_boundary == "Production site boundary" or input.is_empty():
        if input.is_empty():
                return

        # Transmission system properties
        station_outlet_press = self.press_drop_per_dist * self.transmission_freq + self.transmission_inlet_press



