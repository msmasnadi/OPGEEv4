
from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class AcidGasRemoval(Process):
    def run(self, analysis):
        self.print_running_msg()