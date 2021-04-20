from ..process import Process
from ..log import getLogger

_logger = getLogger(__name__)

# TBD: resolve naming issue
class CrudeTransport(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class CrudeOilTransport(Process):
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

class GasStorageWells(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class StorageSeparator(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class GasTransmissionCompressors(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class DiluentTransport(Process):
    def run(self, **kwargs):
        self.print_running_msg()

class PetcokeTransport(Process):
    def run(self, **kwargs):
        self.print_running_msg()
