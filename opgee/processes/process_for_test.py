from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class AfterDewatering(Process):
    def run(self, analysis):
        self.print_running_msg()


class GasFloodingCompressor(Process):
    def run(self, analysis):
        self.print_running_msg()


class CrudeOilTransport(Process):
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


class SeparationTemporary(Process):
    def run(self, analysis):
        self.print_running_msg()




class FluidProduction(Process):
    def run(self, analysis):
        self.print_running_msg()


class FluidInjection(Process):
    def run(self, analysis):
        self.print_running_msg()


class SourGasInjectionWells(Process):
    def run(self, analysis):
        self.print_running_msg()

class GasTransmissionCompressors(Process):
    def run(self, analysis):
        self.print_running_msg()


class GasPartitionA(Process):
    def run(self, analysis):
        self.print_running_msg()



class GasPartitionB(Process):
    def run(self, analysis):
        self.print_running_msg()


class FuelGasConsumed(Process):
    def run(self, analysis):
        self.print_running_msg()


class FuelGasImports(Process):
    def run(self, analysis):
        self.print_running_msg()

class GasTransmissionCompressors(Process):
    def run(self, analysis):
        self.print_running_msg()


class NGLOrDiluentProdAndImports(Process):
    def run(self, analysis):
        self.print_running_msg()


class Maintenance(Process):
    def run(self, analysis):
        self.print_running_msg()


class WasteDisposal(Process):
    def run(self, analysis):
        self.print_running_msg()


class GasStorageWells(Process):
    def run(self, analysis):
        self.print_running_msg()

class PetcokeTransport(Process):
    def run(self, analysis):
        self.print_running_msg()


class ElectricityGenAndImports(Process):
    def run(self, analysis):
        self.print_running_msg()