from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class CrudeStorage(Process):
    def run(self, analysis):
        self.print_running_msg()


class GasLiftingCompressor(Process):
    def run(self, analysis):
        self.print_running_msg()


class BitumenMining(Process):
    def run(self, analysis):
        self.print_running_msg()

    def impute(self):
        # TBD: copy from output streams to input streams
        pass


class WaterInjection(Process):
    def run(self, analysis):
        self.print_running_msg()


class GasReinjectionCompressor(Process):
    def run(self, analysis):
        self.print_running_msg()


class GasFloodingCompressor(Process):
    def run(self, analysis):
        self.print_running_msg()


class CO2ReinjectionCompressor(Process):
    def run(self, analysis):
        self.print_running_msg()


class SourGasReinjectionCompressor(Process):
    def run(self, analysis):
        self.print_running_msg()


class HCGasInjectionWells(Process):
    def run(self, analysis):
        self.print_running_msg()


class CO2InjectionWells(Process):
    def run(self, analysis):
        self.print_running_msg()


class GasFloodWells(Process):
    def run(self, analysis):
        self.print_running_msg()


class SteamInjectionWells(Process):
    def run(self, analysis):
        self.print_running_msg()


class Flaring(Process):
    def run(self, analysis):
        self.print_running_msg()

