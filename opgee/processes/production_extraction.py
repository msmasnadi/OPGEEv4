from ..core import Process
from ..log import getLogger

_logger = getLogger(__name__)

class DownholePump(Process):
    #
    # Note that in v3, the input streams are just references to the output streams
    #
    def __init__(self, name, attr_dict=None):
        inputs = [3, 101, 26, 42]
        outputs = [4, 102, 27, 250, 283, 284, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296]

        super().__init__(name, inputs=inputs, outputs=outputs, attr_dict=attr_dict)

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

