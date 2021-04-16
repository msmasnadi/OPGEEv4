from ..core import Process
from ..log import getLogger

_logger = getLogger(__name__)

class ReservoirWellInterface(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)
