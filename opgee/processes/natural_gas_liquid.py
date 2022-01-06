from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class NGL(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()

    def run(self, analysis):
        self.print_running_msg()
