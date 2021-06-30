from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class CrudeOilStabilization(Process):
    def run(self, analysis):
        self.print_running_msg()

        field = self.get_field()
        stab_temp = self.attr("stab_temp")
        stab_press = self.attr("stab_press")

        # mass rate
        input = self.find_input_streams("oil for stabilization")




