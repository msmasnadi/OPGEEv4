from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class GasPartition(Process):
    """
    Gas partition is to check the reasonable amount of gas goes to gas lifting and gas reinjection

    """
    def run(self, analysis):
        self.print_running_msg()
