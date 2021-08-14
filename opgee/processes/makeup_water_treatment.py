from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class MakeupWaterTreatment(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()

    def run(self, analysis):
        self.print_running_msg()

    def impute(self):
        # mass rate
        output = self.find_output_stream("water for steam generation")