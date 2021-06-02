from ..log import getLogger
from ..process import Process
from ..thermodynamics import OilGasWater
from ..drivers import Drivers
from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY
from ..emissions import Emissions
from opgee import ureg
from opgee.stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID

_logger = getLogger(__name__)

dict_chemical = OilGasWater.get_dict_chemical()
_power = [1, 1 / 2, 1 / 3, 1 / 4, 1 / 5]


def get_compression_ratio_stages(overall_compression_ratio_stages):
    max_stages = len(_power)
    compression_ratio_per_stages = []

    for compression_ratio in overall_compression_ratio_stages:
        for pow in _power:
            if compression_ratio ** pow < max_stages:
                compression_ratio_per_stages.append(compression_ratio ** pow)
                break

    return compression_ratio_per_stages


def get_num_of_compression_stages(overall_compression_ratio_stages, compression_ratio_per_stages):
    num_of_compression_stages = []

    for overall_compression_ratio, compression_ratio in \
            zip(overall_compression_ratio_stages, compression_ratio_per_stages):
        for pow in _power:
            if overall_compression_ratio ** pow == compression_ratio:
                num_of_compression_stages.append(int(1 / pow))
                break

    return num_of_compression_stages


def get_energy_consumption_stages(prime_mover_type, brake_horsepower_of_stages):
    energy_consumption_of_stages = []
    for brake_horsepower in brake_horsepower_of_stages:
        eff = Drivers.get_efficiency(prime_mover_type, brake_horsepower)
        energy_consumption = (brake_horsepower * eff).to("mmBtu/day")
        energy_consumption_of_stages.append(energy_consumption)

    return energy_consumption_of_stages


class Separation(Process):
    def run(self, analysis):
        self.print_running_msg()

        field = self.get_field()
        temperature_outlet = self.attr("temperature_outlet")
        pressure_after_boosting = self.attr("gas_pressure_after_boosting")

        # mass rate
        input = self.find_input_stream("crude oil")

        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_after_separation = self.find_output_stream("gas")

        loss_rate = self.venting_fugitive_rate()
        # gas_after_separation.copy_gas_rates_from(input)
        # gas_after_separation.multiply_flow_rates(1 / (1 + loss_rate))
        # gas_fugitives = self.set_gas_fugitives(gas_after_separation, "gas fugitives from separator")

        # temperature and pressure

        # energy rate
        oil_volume_rate = field.attr("oil_prod")  # (float) bbl/day
        compressor_eff = self.attr("eta_compressor").to("frac")
        # Primary mover type is one of: {"NG_engine", "Electric_motor", "Diesel_engine", "NG_turbine"}
        prime_mover_type = self.attr("prime_mover_type")

        free_gas_stages = self.get_free_gas_stages(field)  # (float, list) scf/bbl
        gas_compression_volume_stages = [(oil_volume_rate * free_gas).to("mmscf/day") for free_gas in free_gas_stages]
        compressor_horsepower_of_stages = self.compressor_horsepower_of_stages(field,
                                                                               gas_after_separation,
                                                                               gas_compression_volume_stages)
        brake_horsepower_of_stages = [compressor_hp / compressor_eff
                                      for compressor_hp in compressor_horsepower_of_stages]
        energy_consumption_of_stages = get_energy_consumption_stages(prime_mover_type, brake_horsepower_of_stages)
        energy_consumption_sum = sum(energy_consumption_of_stages)

        energy_use = self.energy
        energy_carrier = EN_NATURAL_GAS if prime_mover_type == "NG_engine" else EN_ELECTRICITY
        energy_use.set_rate(energy_carrier, energy_consumption_sum)

        # emission rate
        emissions = self.emissions

    def impute(self):
        field = self.get_field()

        wellhead_temp = field.attr("wellhead_temperature")
        wellhead_press = field.attr("wellhead_pressure")

        gas_after, oil_after, water_after = self.get_output_streams(field)
        loss_rate = self.venting_fugitive_rate()
        gas_fugitives = self.set_gas_fugitives(gas_after)

        output = Stream.combine([oil_after, gas_after, water_after, gas_fugitives],
                                temperature=wellhead_temp, pressure=wellhead_press)

        input = self.find_input_stream("crude oil")
        input.set_temperature_and_pressure(wellhead_temp, wellhead_press)
        input.copy_flow_rates_from(output)

    def get_stages_temperature_and_pressure(self, field):
        temperature_outlet = self.attr("temperature_outlet")
        temperature_stage1 = field.attr("wellhead_temperature")
        temperature_stage2 = (temperature_stage1.to("kelvin") + temperature_outlet.to("kelvin")) / 2
        temperature_of_stages = [temperature_stage1, temperature_stage2.to("degF"), temperature_outlet]

        pressure_stage1 = self.attr("pressure_first_stage")
        pressure_stage2 = self.attr("pressure_second_stage")
        pressure_stage3 = self.attr("pressure_third_stage")
        pressure_of_stages = [pressure_stage1, pressure_stage2, pressure_stage3]

        return temperature_of_stages, pressure_of_stages

    def get_output_streams(self, field):
        oil_volume_rate = field.attr("oil_prod")  # (float) bbl/day

        gas_oil_ratio = field.attr("GOR")  # (float) scf/bbl
        gas_comp = field.attrs_with_prefix("gas_comp_")  # Pandas.Series (float) percent

        water_oil_ratio = field.attr("WOR")

        num_of_stages = self.attr("number_stages")

        std_temp = field.model.const("std-temperature")
        temperature_outlet = self.attr("temperature_outlet")
        std_press = field.model.const("std-pressure")
        pressure_after_boosting = self.attr("gas_pressure_after_boosting")
        pressure_outlet = self.attr("pressure_outlet")
        temperature_of_stages, pressure_of_stages = self.get_stages_temperature_and_pressure(field)

        oil = field.oil

        gas_after = field.find_stream("gas after separator")
        stream = Stream("stage_stream",
                        temperature=temperature_of_stages[num_of_stages - 1],
                        pressure=pressure_of_stages[num_of_stages - 1])

        density = oil.density(stream,  # lb/ft3
                              oil.oil_specific_gravity,
                              oil.gas_specific_gravity,
                              oil.gas_oil_ratio)

        for component, mol_frac in gas_comp.items():
            gas_volume_rate = oil_volume_rate * gas_oil_ratio * mol_frac.to("frac")
            gas_density = oil.rho(component, std_temp, std_press, PHASE_GAS)
            gas_mass_rate = (gas_volume_rate * gas_density).to("tonne/day")
            gas_after.set_gas_flow_rate(component, gas_mass_rate)
        gas_after.set_temperature_and_pressure(temperature_outlet, pressure_after_boosting)

        oil_after = field.find_stream("oil after separator")
        oil_mass_rate = (oil_volume_rate * density).to("tonne/day")
        water_in_oil_mass_rate = (oil_mass_rate * self.attr("water_content_oil_emulsion")).to("tonne/day")
        oil_after.set_liquid_flow_rate("oil", oil_mass_rate)
        oil_after.set_liquid_flow_rate("H2O", water_in_oil_mass_rate)
        oil_after.set_temperature_and_pressure(temperature_outlet, pressure_outlet)

        water_density_STP = field.oil.rho("H2O", std_temp, std_press, PHASE_LIQUID)
        water_mass_rate = (oil_volume_rate * water_oil_ratio * water_density_STP.to("tonne/barrel_water") -
                           water_in_oil_mass_rate)
        water_after = field.find_stream("water after separator")
        water_after.set_liquid_flow_rate("H2O", water_mass_rate)
        water_after.set_temperature_and_pressure(temperature_outlet, pressure_outlet)
        return gas_after, oil_after, water_after

    def get_free_gas_stages(self, field):
        oil = field.oil

        num_of_stages = self.attr("number_stages")
        temperature_of_stages, pressure_of_stages = self.get_stages_temperature_and_pressure(field)

        solution_gas_oil_ratio_of_stages = [oil.gas_oil_ratio]
        for stage in range(num_of_stages):
            stream_stages = Stream("stage_stream",
                                   temperature=temperature_of_stages[stage],
                                   pressure=pressure_of_stages[stage])
            solution_gas_oil_ratio = oil.solution_gas_oil_ratio(stream_stages,
                                                                oil.oil_specific_gravity,
                                                                oil.gas_specific_gravity,
                                                                oil.gas_oil_ratio)
            solution_gas_oil_ratio_of_stages.append(solution_gas_oil_ratio)

        free_gas_of_stages = []
        for i in range(1, len(solution_gas_oil_ratio_of_stages)):
            free_gas_of_stages.append(solution_gas_oil_ratio_of_stages[i - 1] -
                                      solution_gas_oil_ratio_of_stages[i])

        return free_gas_of_stages

    def compressor_horsepower_of_stages(self, field, gas_stream, gas_compression_volume_stages):
        gas = field.gas

        num_of_stages = self.attr("number_stages")
        temperature_of_stages, pressure_of_stages = self.get_stages_temperature_and_pressure(field)
        pressure_after_boosting = self.attr("gas_pressure_after_boosting")

        overall_compression_ratio_stages = [pressure_after_boosting /
                                            pressure_of_stages[stage] for stage in range(num_of_stages)]
        compression_ratio_per_stages = get_compression_ratio_stages(overall_compression_ratio_stages)
        num_of_compression_stages = get_num_of_compression_stages(overall_compression_ratio_stages,
                                                                  compression_ratio_per_stages)  # (int)

        horsepower_of_stages = []
        for (inlet_temp, inlet_press, compression_ratio,
             gas_compression_volume, num_of_compression) \
                in zip(temperature_of_stages,
                       pressure_of_stages,
                       compression_ratio_per_stages,
                       gas_compression_volume_stages,
                       num_of_compression_stages):
            work = 0
            for j in range(num_of_compression):
                inlet_reduced_temp = inlet_temp.to("rankine") / gas.corrected_pseudocritical_temperature(gas_stream)
                inlet_reduced_press = inlet_press / gas.corrected_pseudocritical_pressure(gas_stream)
                z_factor = gas.Z_factor(inlet_reduced_temp, inlet_reduced_press)
                ratio_of_specific_heat = gas.ratio_of_specific_heat(gas_stream)

                work_temp1 = 3.027 * 14.7 / (60 + 460) * ratio_of_specific_heat / (ratio_of_specific_heat - 1)
                ratio = (ratio_of_specific_heat - 1) / ratio_of_specific_heat
                work_temp2 = (compression_ratio ** z_factor) ** ratio - 1
                work += work_temp1 * work_temp2 * inlet_temp.to("rankine")

                delta_temp = (inlet_temp.to("rankine") *
                              compression_ratio ** (z_factor * ratio) - inlet_temp) * 0.2
                inlet_temp = ureg.Quantity(inlet_temp.m + delta_temp.m, "degF")
                inlet_press = (compression_ratio * inlet_press if j == 0 else
                               inlet_press * compression_ratio * num_of_compression)

            work_sum = ureg.Quantity(work.m, "hp*day/mmscf")
            horsepower = work_sum * gas_compression_volume
            horsepower_of_stages.append(horsepower)

        return horsepower_of_stages
