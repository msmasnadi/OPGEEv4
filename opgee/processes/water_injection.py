from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class WaterInjection(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.water_reinjeciton = field.attr("water_reinjeciton")
        self.water_flooding = field.attr("water_flooding")

        if self.water_reinjeciton == 0 and self.water_flooding == 0:
            self.enabled = False
            return

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("produced water for water injection")