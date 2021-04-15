from ..core import Process
from ..log import getLogger

_logger = getLogger(__name__)


class Separation(Process):
    def __init__(self, name, attr_dict=None):
        inputs = [4, 102, 27]
        outputs = [28, 7, 103, 251]

        super().__init__(name, inputs=inputs, outputs=outputs, attr_dict=attr_dict)

    def run(self, level, **kwargs):
        self.print_running_msg(level)


class ProducedWaterTreatment(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class MakeupWaterTreatment(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class SteamGeneration(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CrudeOilDewatering(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CrudeOilStabilization(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class HeavyOilUpgrading(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class HeavyOilDilution(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class GasGathering(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class GasDehydration(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class AcidGasRemoval(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Demethanizer(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Chiller(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class PreMembraneCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CO2Membrane(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class RyanHolmes(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class VRUCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Venting(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)
