from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class MakeupWaterTreatment(Process):
    def run(self, analysis):
        self.print_running_msg()


class SteamGeneration(Process):
    def run(self, analysis):
        self.print_running_msg()


# A temporary "end process" for testing. Used in opgee.xml.
class AfterDewatering(Process):
    def run(self, analysis):
        self.print_running_msg()


class HeavyOilUpgrading(Process):
    def run(self, analysis):
        self.print_running_msg()


class HeavyOilDilution(Process):
    def run(self, analysis):
        self.print_running_msg()


class GasGathering(Process):
    def run(self, analysis):
        self.print_running_msg()


class GasDehydration(Process):
    def run(self, analysis):
        self.print_running_msg()


class AcidGasRemoval(Process):
    def run(self, analysis):
        self.print_running_msg()


class Demethanizer(Process):
    def run(self, analysis):
        self.print_running_msg()


class Chiller(Process):
    def run(self, analysis):
        self.print_running_msg()


class PreMembraneCompressor(Process):
    def run(self, analysis):
        self.print_running_msg()


class CO2Membrane(Process):
    def run(self, analysis):
        self.print_running_msg()


class RyanHolmes(Process):
    def run(self, analysis):
        self.print_running_msg()


class VRUCompressor(Process):
    def run(self, analysis):
        self.print_running_msg()


class Venting(Process):
    def run(self, analysis):
        self.print_running_msg()
