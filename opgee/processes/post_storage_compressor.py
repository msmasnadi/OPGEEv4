from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..log import getLogger
from ..process import Process
from ..stream import Stream
from .compressor import Compressor
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class PostStorageCompressor(Process):
    """
    Storage compressor calculate emission from compressing produced gas for long-term (i.e., seasonal) storage.
    """
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.discharge_press = self.attr("discharge_press")
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas for storage")

        if input.is_uninitialized():
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp, tp=self.std_tp)

        input_energy_flow_rate = self.field.gas.energy_flow_rate(input)

        overall_compression_ratio = self.discharge_press / input.tp.P
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
        fuel_gas_stream = Stream("fuel gas stream", input.tp)
        fuel_gas_stream.copy_gas_rates_from(input, tp=input.tp)
        fuel_gas_stream.multiply_flow_rates(gas_consumption_frac.m)

        gas_to_distribution = self.find_output_stream("gas for distribution")
        gas_to_distribution.copy_gas_rates_from(input)
        gas_to_distribution.tp.set(T=output_temp, P=self.discharge_press)

        gas_to_distribution.subtract_gas_rates_from(fuel_gas_stream)
        gas_to_distribution.subtract_gas_rates_from(gas_fugitives)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.set_rate(EM_COMBUSTION, "CO2", combustion_emission)
        emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)
