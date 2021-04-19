from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)

class Drilling(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class LandUse(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class Fracking(Process):
    def run(self, **kwargs):
        self.print_running_msg()
