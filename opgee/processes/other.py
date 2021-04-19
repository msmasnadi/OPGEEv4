from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)


class FluidProduction(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class FluidInjection(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class Maintenance(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class CrudeSeparationAndHandling(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class CrudeTransport(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class BitumenUpgradingOrDistilation(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class WasteTreatmentAndDisposal(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class DrillingAndDevelopment(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class CrudeOilStorage(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class StorageCompressor(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class PostStorageCompressor(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class SourGasInjectionWells(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class GasStorageWells(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class StorageSeparator(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class GasTransmissionCompressors(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class GasPartitionA(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class GasPartitionB(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class FuelGasConsumed(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class FuelGasImports(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class WasteDisposal(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class CrudeOilTransport(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class DiluentTransport(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class PetcokeTransport(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class GasDistribution(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class ElectricityGenAndImports(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class NGLOrDiluentProdAndImports(Process):
    def run(self, **kwargs):
        self.print_running_msg()
