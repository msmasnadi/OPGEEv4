from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class LNGLiquefaction(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class LNGTransport(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class LNGRegasification(Process):
    def run(self, **kwargs):
        self.print_running_msg()
