from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)

# TBD: resolve naming issue
class Drilling(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class DrillingAndDevelopment(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class LandUse(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class Fracking(Process):
    def run(self, **kwargs):
        self.print_running_msg()
