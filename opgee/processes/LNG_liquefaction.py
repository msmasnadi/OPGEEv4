from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class LNGLiquefaction(Process):
    def run(self, analysis):
        self.print_running_msg()