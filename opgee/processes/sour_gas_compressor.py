from .. import ureg
from ..compressor import Compressor
from ..emissions import EM_COMBUSTION, EM_FUGITIVES
from ..log import getLogger
from ..process import Process
from .shared import get_energy_carrier

_logger = getLogger(__name__)


class SourGasCompressor(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.res_press = field.attr("res_press")
        self.eta_compressor = self.attr("eta_compressor")
        self.prime_mover_type = self.attr("prime_mover_type")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_stream("gas for sour gas compressor")

        if input.is_uninitialized():
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

        gas_to_injection = self.find_output_stream("gas for sour gas injection")
        gas_to_injection.copy_flow_rates_from(input)
        gas_to_injection.subtract_gas_rates_from(gas_fugitives)

        discharge_press = self.res_press + ureg.Quantity(500, "psi")
        overall_compression_ratio = discharge_press / input.pressure
        compression_ratio = Compressor.get_compression_ratio(overall_compression_ratio)
        num_stages = Compressor.get_num_of_compression(overall_compression_ratio)
        total_work, temp, _ = Compressor.get_compressor_work_temp(self.field,
                                                               input.temperature,
                                                               input.pressure,
                                                               input,
                                                               compression_ratio,
                                                               num_stages)
        volume_flow_rate_STP = self.gas.tot_volume_flow_rate_STP(input)
        total_energy = total_work * volume_flow_rate_STP
        brake_horse_power = total_energy / self.eta_compressor
        energy_consumption = self.get_energy_consumption(self.prime_mover_type, brake_horse_power.to("horsepower"))

        gas_to_injection.set_temperature_and_pressure(temp, input.pressure)

        self.field.save_process_data(CO2_injection_rate=gas_to_injection.gas_flow_rate("CO2"))

        # energy-use
        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)



