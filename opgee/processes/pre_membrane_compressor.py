from ..log import getLogger
from ..process import Process
from ..stream import PHASE_LIQUID
from ..compressor import Compressor
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from ..emissions import Emissions, EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class PreMembraneCompressor(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")

        # TODO: choose whether to use PMC as prefix or suffix, but not both. The random approach makes it harder to remember names.
        self.PMC_discharge_press = field.attr("PMC_discharge_press")
        self.eta_compressor_PMC = field.attr("eta_compressor_PMC")
        self.prime_mover_type_PMC = field.attr("prime_mover_type_PMC")

    def run(self, analysis):
        self.print_running_msg()

        input = self.find_input_stream("gas for compressor")

        if input.is_empty():
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

        gas_to_CO2_membrane = self.find_output_stream("gas for CO2 membrane")
        gas_to_CO2_membrane.copy_flow_rates_from(input)
        gas_to_CO2_membrane.subtract_gas_rates_from(gas_fugitives)

        overall_compression_ratio = self.PMC_discharge_press / input.pressure
        compression_ratio = Compressor.get_compression_ratio(overall_compression_ratio)
        num_stages = Compressor.get_num_of_compression(overall_compression_ratio)
        total_work, outlet_temp, outlet_press = Compressor.get_compressor_work_temp(self.field,
                                                            input.temperature,
                                                            input.pressure,
                                                            input,
                                                            compression_ratio,
                                                            num_stages)
        gas_to_CO2_membrane.set_temperature_and_pressure(outlet_temp, input.pressure)
        volume_flow_rate_STP = self.gas.tot_volume_flow_rate_STP(input)
        total_energy = total_work * volume_flow_rate_STP
        brake_horse_power = total_energy / self.eta_compressor_PMC
        energy_consumption = self.get_energy_consumption(self.prime_mover_type_PMC, brake_horse_power)

        # energy-use
        energy_use = self.energy
        if self.prime_mover_type_PMC == "NG_engine" or "NG_turbine":
            energy_carrier = EN_NATURAL_GAS
        elif self.prime_mover_type_PMC == "Electric_motor":
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


