from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)

class Exploration(Process):
    def run(self, analysis):
        self.print_running_msg()

        m = self.model
        dens = m.const('amb-air-density')
        pres = m.const('amb-pressure')

class SurveyTruck(Process):
    def run(self, analysis):
        self.print_running_msg()

    def __str__(self):
        return f'<SurveyTruck>'

class SurveyShip(Process):
    def run(self, analysis):
        self.print_running_msg()

    def __str__(self):
        return f'<SurveyShip>'
