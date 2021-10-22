from ..log import getLogger
from ..process import Process
from opgee import ureg
from ..stream import PHASE_LIQUID, PHASE_GAS
from ..compressor import Compressor
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from ..emissions import Emissions, EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES


_logger = getLogger(__name__)


class GasLiftingCompressor(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.gas = field.gas
        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.res_press = field.attr("res_press")
        self.prime_mover_type = self.attr("prime_mover_type")
        self.eta_compressor_lifting = field.attr("eta_compressor_lifting")
        self.prime_mover_type_gas_lifting = field.attr("prime_mover_type_gas_lifting")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_stream("lifting gas")
        press = input.pressure
        temp = input.temperature

        if input.total_flow_rate().m == 0:
            return

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)
        gas_fugitives.set_temperature_and_pressure(self.std_temp, self.std_press)

        lifting_gas = self.find_output_stream("lifting gas")
        lifting_gas.copy_flow_rates_from(input)
        if len(lifting_gas.components.query("gas > 0.0")):
            return

        discharge_press = (self.res_press + press) / 2 + ureg.Quantity(100, "psi")
        overall_compression_ratio = discharge_press / press
        compression_ratio = Compressor.get_compression_ratio(overall_compression_ratio)
        num_stages = Compressor.get_num_of_compression(overall_compression_ratio)
        total_work, _ = Compressor.get_compressor_work_temp(self.field, temp, press, lifting_gas, compression_ratio,
                                                            num_stages)
        volume_flow_rate_STP = self.gas.tot_volume_flow_rate_STP(lifting_gas)
        total_energy = total_work * volume_flow_rate_STP
        brake_horse_power = total_energy / self.eta_compressor_lifting
        energy_consumption = self.get_energy_consumption(self.prime_mover_type_gas_lifting, brake_horse_power)
        energy_content_imported_gas = self.gas.mass_energy_density(lifting_gas) * lifting_gas.total_gas_rate()
        frac_imported_gas_consumed = energy_consumption / energy_content_imported_gas
        gas_lifting_fugitive_loss_rate = self.field.get_process_data("gas_lifting_compressor_loss_rate")
        loss_rate = (ureg.Quantity(0, "frac")
                     if gas_lifting_fugitive_loss_rate is None else gas_lifting_fugitive_loss_rate)
        factor = 1 - loss_rate - frac_imported_gas_consumed
        lifting_gas.multiply_flow_rates(factor.m)

        # energy-use
        energy_use = self.energy
        if self.prime_mover_type == "NG_engine" or "NG_turbine":
            energy_carrier = EN_NATURAL_GAS
        elif self.prime_mover_type == "Electric_motor":
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

        if self.field.get_process_data("methane_from_gas_lifting") is None:
            self.field.save_process_data(methane_from_gas_lifting=lifting_gas.components.loc["C1", PHASE_GAS])
        pass

