from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID
from ..compressor import Compressor
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from ..emissions import Emissions, EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class VRUCompressor(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.discharge_press = field.attr("VRU_discharge_press")
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.prime_mover_type_VRU = field.attr("prime_mover_type_VRU")
        self.eta_compressor_VRU = field.attr("eta_compressor_VRU")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_stream("gas for VRU")

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

        gas_to_gathering = self.find_output_stream("gas for gas gathering")
        gas_to_gathering.copy_flow_rates_from(input)
        gas_to_gathering.subtract_gas_rates_from(gas_fugitives)

        overall_compression_ratio = self.discharge_press / input.pressure
        compression_ratio = Compressor.get_compression_ratio(overall_compression_ratio)
        num_stages = Compressor.get_num_of_compression(overall_compression_ratio)
        total_work, temp = Compressor.get_compressor_work_temp(self.field,
                                                               input.temperature, input.pressure, input,
                                                               compression_ratio,
                                                               num_stages)

        gas_to_gathering.set_temperature_and_pressure(temp, self.discharge_press)

        volume_flow_rate_STP = self.gas.tot_volume_flow_rate_STP(input)
        total_energy = total_work * volume_flow_rate_STP
        brake_horse_power = total_energy / self.eta_compressor_VRU
        energy_consumption = self.get_energy_consumption(self.prime_mover_type_VRU, brake_horse_power)

        # energy-use
        energy_use = self.energy
        if self.prime_mover_type_VRU == "NG_engine" or "NG_turbine":
            energy_carrier = EN_NATURAL_GAS
        elif self.prime_mover_type_VRU == "Electric_motor":
            energy_carrier = EN_ELECTRICITY
        else:
            energy_carrier = EN_DIESEL
        energy_use.set_rate(energy_carrier, energy_consumption)

        # emissions
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)
