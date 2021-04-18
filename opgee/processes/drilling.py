from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)

class Drilling(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class LandUse(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Fracking(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)
