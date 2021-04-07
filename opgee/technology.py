from .core import Technology
from .log import getLogger

_logger = getLogger(__name__)

# Techs used in test XML file
class t1(Technology):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class t2(Technology):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class t3(Technology):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class SurveyVehicle(Technology):
    pass

class Drilling(Technology):
    pass

class LandUse(Technology):
    pass
