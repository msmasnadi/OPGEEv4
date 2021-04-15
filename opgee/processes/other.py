from ..core import Process
from ..log import getLogger

_logger = getLogger(__name__)


class FluidProduction(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class FluidInjection(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Maintenance(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CrudeSeparationAndHandling(Process):
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

class DrillingAndDevelopment(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class CrudeOilStorage(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class StorageCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class PostStorageCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class SourGasInjectionWells(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class GasStorageWells(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class StorageSeparator(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class GasTransmissionCompressors(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class GasPartitionA(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class GasPartitionB(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class FuelGasConsumed(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class FuelGasImports(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class WasteDisposal(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class CrudeOilTransport(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class DiluentTransport(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class PetcokeTransport(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class GasDistribution(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class ElectricityGenAndImports(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class NGLOrDiluentProdAndImports(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)
