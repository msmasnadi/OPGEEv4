from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)

class Exploration(Process):
    def run(self, **kwargs):
        self.print_running_msg()

        m = self.model
        dens = m.const('amb-air-density')
        pres = m.const('amb-pressure')

class SurveyVehicle(Process):
    def run(self, **kwargs):
        self.print_running_msg()

    def __str__(self):
        type_attr = self.attr_dict['type']
        return f'<SurveyVehicle type="{type_attr.value}">'
