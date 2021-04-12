from .core import Process
from .log import getLogger

_logger = getLogger(__name__)

# Processes used in test XML file
class t1(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class t2(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class t3(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Drilling(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class LandUse(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Fracking(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class SurveyVehicle(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class ReservoirWellInterface(Process):
    # Streams in:  1, 100, 25, 91
    # Streams out: 3, 101, 26
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class WellAndDownholePump(Process):
    # Streams in:  3, 101, 26, 42
    # Streams out: 4, 102, 27, 250, 283, 284, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Separation(Process):
    # Streams in:  4, 102, 27
    # Streams out: 28, 7, 103, 251
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class FluidProduction(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class FluidInjection(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class BitumenMining(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Maintenance(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CrudeSeparationAndHandling(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CrudeStorage(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CrudeTransport(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class BitumenUpgradingOrDistilation(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class WasteTreatmentAndDisposal(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

