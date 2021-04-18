from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class LNGLiquefaction(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class LNGTransport(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class LNGRegasification(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)
