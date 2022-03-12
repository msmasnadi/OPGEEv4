from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)

# TBD: resolve naming issue
class Drilling(Process):
    def run(self, analysis):
        self.print_running_msg()
