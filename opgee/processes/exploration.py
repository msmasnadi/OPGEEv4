from ..core import Process
from ..log import getLogger

_logger = getLogger(__name__)

class Exploration(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class SurveyVehicle(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

    def __str__(self):
        type_attr = self.attr_dict['type']
        return f'<SurveyVehicle type="{type_attr.value}">'
