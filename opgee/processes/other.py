from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class FluidProduction(Process):
    def run(self, analysis):
        self.print_running_msg()


class FluidInjection(Process):
    def run(self, analysis):
        self.print_running_msg()


class Maintenance(Process):
    def run(self, analysis):
        self.print_running_msg()


class CrudeSeparationAndHandling(Process):
    def run(self, analysis):
        self.print_running_msg()


class BitumenUpgradingOrDistilation(Process):
    def run(self, analysis):
        self.print_running_msg()


class WasteTreatmentAndDisposal(Process):
    def run(self, analysis):
        self.print_running_msg()

class SourGasInjectionWells(Process):
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

class WasteDisposal(Process):
    def run(self, analysis):
        self.print_running_msg()

class GasDistribution(Process):
    def run(self, analysis):
        self.print_running_msg()

class ElectricityGenAndImports(Process):
    def run(self, analysis):
        self.print_running_msg()

class NGLOrDiluentProdAndImports(Process):
    def run(self, analysis):
        self.print_running_msg()
