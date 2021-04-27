from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__) #data logging

class ReservoirWellInterface(Process):
    def run(self, **kwargs):
        _logger.debug("stream")
        field = self.get_field()
        self.print_running_msg()

    def impute(self):
        # TBD: copy from output streams to input streams
        pass