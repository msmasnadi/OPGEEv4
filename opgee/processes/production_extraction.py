from ..core import Process
from ..log import getLogger

_logger = getLogger(__name__)

class DownholePump(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CrudeStorage(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class GasLiftingCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class BitumenMining(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class WaterInjection(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class GasReinjectionCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class GasFloodingCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CO2ReinjectionCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class SourGasReinjectionCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class HCGasInjectionWells(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CO2InjectionWells(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class GasFloodWells(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class SteamInjectionWells(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Flaring(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

