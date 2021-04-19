from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)

class Exploration(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class SurveyVehicle(Process):
    def run(self, **kwargs):
        self.print_running_msg()

    def __str__(self):
        type_attr = self.attr_dict['type']
        return f'<SurveyVehicle type="{type_attr.value}">'
