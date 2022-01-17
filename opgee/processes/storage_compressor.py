from ..stream import Stream, PHASE_GAS
from .shared import get_energy_carrier
from opgee.processes.compressor import Compressor
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..log import getLogger
from ..process import Process

_logger = getLogger(__name__)


class StorageCompressor(Process):
    """
    Storage compressor calculate emission from compressing gas for long-term (i.e., seasonal) storage.

    """

    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.discharge_press = self.attr("discharge_press")
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        input = self.find_input_stream("gas for storage")

        if input.has_zero_flow():
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp, temp=field.std_temp, press=field.std_press)

        input_energy_flow_rate = self.field.gas.energy_flow_rate(input)

        overall_compression_ratio = self.discharge_press / input.pressure
        energy_consumption, output_temp, output_press = \
            Compressor.get_compressor_energy_consumption(
                self.field,
                self.prime_mover_type,
                self.eta_compressor,
                overall_compression_ratio,
                input)

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption)

        gas_consumption_frac = energy_use.get_rate(energy_carrier) / input_energy_flow_rate
        fuel_gas_stream = Stream("fuel gas stream", temperature=input.temperature, pressure=input.pressure)
        fuel_gas_stream.copy_flow_rates_from(input, phase=PHASE_GAS)
        fuel_gas_stream.multiply_flow_rates(gas_consumption_frac.m)

        gas_to_well = self.find_output_stream("gas for well")
        gas_to_well.copy_flow_rates_from(input, phase=PHASE_GAS, temp=output_temp, press=self.discharge_press)
        gas_to_well.subtract_gas_rates_from(fuel_gas_stream)
        gas_to_well.subtract_gas_rates_from(gas_fugitives)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)