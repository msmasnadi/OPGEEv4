from .core import Process
from .log import getLogger

_logger = getLogger(__name__)

class Drilling(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class LandUse(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Fracking(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class SurveyVehicle(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

    def __str__(self):
        type_attr = self.attr_dict['type']
        return f'<SurveyVehicle type="{type_attr.value}">'


class ReservoirWellInterface(Process):
    def __init__(self, name, attr_dict=None):
        inputs  = [1, 100, 25, 91]
        outputs = [3, 101, 26]

        super().__init__(name, inputs=inputs, outputs=outputs, attr_dict=attr_dict)


    def run(self, level, **kwargs):
        self.print_running_msg(level)


class WellAndDownholePump(Process):
    #
    # Note that in v3, the input streams are just references to the output streams
    #
    def __init__(self, name, attr_dict=None):
        inputs = [3, 101, 26, 42]
        outputs = [4, 102, 27, 250, 283, 284, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296]

        super().__init__(name, inputs=inputs, outputs=outputs, attr_dict=attr_dict)

    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Separation(Process):
    def __init__(self, name, attr_dict=None):
        inputs = [4, 102, 27]
        outputs = [ 28, 7, 103, 251]

        super().__init__(name, inputs=inputs, outputs=outputs, attr_dict=attr_dict)

    def run(self, level, **kwargs):
        self.print_running_msg(level)


class FluidProduction(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class FluidInjection(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class BitumenMining(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Maintenance(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CrudeSeparationAndHandling(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)


class CrudeStorage(Process):
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

class Exploration(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class DrillingAndDevelopment(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class Reservoir(Process):
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

class CrudeOilStorage(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class SteamGeneration(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class ProducedWaterTreatment(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class MakeupWaterTreatment(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class WaterInjection(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class Flaring(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class Venting(Process):
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

class CO2Membrane(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class Ryan_Holmes(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class GasReinjectionCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class GasLiftingCompressor(Process):
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

class VRUCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class Pre_MembraneCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class LNGLiquefaction(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class LNGTransport(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class LNGRegasification(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class StorageCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class Post_StorageCompressor(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class HCGasInjectionWells(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class CO2InjectionWells(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class SourGasInjectionWells(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class SteamInjectionWells(Process):
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class GasFloodWells(Process):
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
