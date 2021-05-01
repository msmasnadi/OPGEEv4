from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID

_logger = getLogger(__name__)


class Separation(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class MakeupWaterTreatment(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class SteamGeneration(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class CrudeOilDewatering(Process):
    # For our initial, highly-simplified test case, we just shuttle the oil and water
    # to two output streams and force the temperature and pressure to what was in the
    # OPGEE v3 workbook for the default field.
    def run(self, **kwargs):
        self.print_running_msg()

        # find appropriate streams by checking connected processes' capabilities
        input_stream = self.find_input_streams('crude oil', combine=True)

        # Split the oil and water from the input stream into two output streams
        oil_rate = input_stream.flow_rate('oil', PHASE_LIQUID)
        H2O_rate = input_stream.flow_rate('H2O', PHASE_LIQUID)

        # TBD: For now, we're assuming only one handler for each type of stream is found
        oil_stream = self.find_output_streams('dewatered crude oil')[0]
        H2O_stream = self.find_output_streams('untreated water')[0]

        oil_stream.set_flow_rate('oil', PHASE_LIQUID, oil_rate)
        H2O_stream.set_flow_rate('H2O', PHASE_LIQUID, H2O_rate)

        # TBD: compute this thermodynamically
        oil_stream.set_temperature_and_pressure(165, 100)
        H2O_stream.set_temperature_and_pressure(165, 100)


class CrudeOilStabilization(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class HeavyOilUpgrading(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class HeavyOilDilution(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class GasGathering(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class GasDehydration(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class AcidGasRemoval(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class Demethanizer(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class Chiller(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class PreMembraneCompressor(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class CO2Membrane(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class RyanHolmes(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class VRUCompressor(Process):
    def run(self, **kwargs):
        self.print_running_msg()


class Venting(Process):
    def run(self, **kwargs):
        self.print_running_msg()
