from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class DownholePump(Process):
    def run(self, analysis):
        self.print_running_msg()

    def impute(self):
        # TBD: copy some output streams to input streams, and
        # TBD: sum rates of some substances from outputs to compute input rates
        field = self.get_field()

        output = self.find_output_streams("crude oil")
        pass