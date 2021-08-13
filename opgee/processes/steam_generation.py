from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class SteamGeneration(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()

    def run(self, analysis):
        self.print_running_msg()
        self.set_iteration_value(0)     # use a constant to end cycle after one iteration

    def impute(self):
        pass
