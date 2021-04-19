from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)

class ReservoirWellInterface(Process):
    def run(self, **kwargs):
        self.print_running_msg()

    def impute(self):
        # TBD: copy from output streams to input streams
        pass
