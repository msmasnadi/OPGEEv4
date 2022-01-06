from opgee.stream import Stream
from ..compressor import Compressor
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
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
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")


    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas for storage")

        if input.has_zero_flow():
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

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
        if self.prime_mover_type == "NG_engine" or "NG_turbine":
            energy_carrier = EN_NATURAL_GAS
        elif self.prime_mover_type == "Electric_motor":
            energy_carrier = EN_ELECTRICITY
        else:
            energy_carrier = EN_DIESEL
        energy_use.set_rate(energy_carrier, energy_consumption)

        gas_consumption_frac = energy_use.get_rate(energy_carrier) / input_energy_flow_rate
        fuel_gas_stream = Stream("fuel gas stream", temperature=input.temperature, pressure=input.pressure)
        fuel_gas_stream.copy_gas_rates_from(input)
        fuel_gas_stream.multiply_flow_rates(gas_consumption_frac.m)
        fuel_gas_stream.set_temperature_and_pressure(temp=input.temperature, press=input.pressure)

        gas_to_well = self.find_output_stream("gas for well")
        gas_to_well.copy_gas_rates_from(input)
        gas_to_well.subtract_gas_rates_from(fuel_gas_stream)
        gas_to_well.subtract_gas_rates_from(gas_fugitives)
        gas_to_well.set_temperature_and_pressure(temp=output_temp, press=self.discharge_press)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combustion_emission)
        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)

