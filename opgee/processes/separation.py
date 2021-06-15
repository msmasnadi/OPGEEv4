from ..log import getLogger
from ..process import Process

from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY
from .. import ureg
from ..stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID
from ..thermodynamics import rho
from ..compressor import Compressor
from ..emissions import EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)

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


class Separation(Process):
    def run(self, analysis):
        self.print_running_msg()

        field = self.get_field()

        # mass rate
        input = self.find_input_stream("crude oil")

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)

        gas_after = self.find_output_stream("gas")
        # Check
        self.set_iteration_value(gas_after.components.sum().sum())
        gas_after.copy_gas_rates_from(input)
        gas_after.subtract_gas_rates_from(gas_fugitives)

        # temperature and pressure

        # energy rate
        oil_volume_rate = field.attr("oil_prod")  # (float) bbl/day

        # Primary mover type is one of: {"NG_engine", "Electric_motor", "Diesel_engine", "NG_turbine"}
        prime_mover_type = self.attr("prime_mover_type")

        free_gas_stages = self.get_free_gas_stages(field)  # (float, list) scf/bbl
        gas_compression_volume_stages = [(oil_volume_rate * free_gas).to("mmscf/day") for free_gas in free_gas_stages]
        compressor_brake_horsepower_of_stages = self.compressor_brake_horsepower_of_stages(field,
                                                                                           gas_after,
                                                                                           gas_compression_volume_stages)
        energy_consumption_of_stages = self.get_energy_consumption_stages(prime_mover_type,
                                                                          compressor_brake_horsepower_of_stages)
        energy_consumption_sum = sum(energy_consumption_of_stages)

        energy_use = self.energy
        energy_carrier = EN_NATURAL_GAS if prime_mover_type == "NG_engine" else EN_ELECTRICITY
        energy_use.set_rate(energy_carrier, energy_consumption_sum)

        # emission rate
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        process_EF = self.get_process_EF()
        combusion_emission = (energy_for_combustion * process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "GHG", combusion_emission)

        gwp_stream = analysis.gwp_stream

        fugitive_emission_stream = Stream("fugitive_emission", temperature=0, pressure=0)
        fugitive_emission_stream.components[PHASE_GAS] = gwp_stream * gas_fugitives.components[PHASE_GAS]
        emissions.add_from_stream(EM_FUGITIVES, fugitive_emission_stream)

    def impute(self):
        field = self.get_field()

        wellhead_temp = field.attr("wellhead_temperature")
        wellhead_press = field.attr("wellhead_pressure")

        gas_after, oil_after, water_after = self.get_output_streams(field)
        loss_rate = self.venting_fugitive_rate()
        loss_rate = (1 / (1 - loss_rate)).to("frac")
        gas_after.multiply_flow_rates(loss_rate)

        output = Stream.combine([oil_after, gas_after, water_after],
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
        gas = field.gas

        gas_after = self.find_output_stream("gas")
        stream = Stream("stage_stream",
                        temperature=temperature_of_stages[num_of_stages - 1],
                        pressure=pressure_of_stages[num_of_stages - 1])

        density = oil.density(stream,  # lb/ft3
                              oil.oil_specific_gravity,
                              oil.gas_specific_gravity,
                              oil.gas_oil_ratio)

        gas_volume_rate = oil_volume_rate * gas_oil_ratio * gas_comp
        gas_density = gas.component_gas_rho_STP[gas_comp.index]
        gas_mass_rate = gas_volume_rate * gas_density

        for component, mass_rate in gas_mass_rate.items():
            gas_after.set_gas_flow_rate(component, mass_rate.to("tonne/day"))
        gas_after.set_temperature_and_pressure(temperature_outlet, pressure_after_boosting)

        oil_after = self.find_output_stream("crude oil")
        oil_mass_rate = (oil_volume_rate * density).to("tonne/day")
        water_in_oil_mass_rate = self.water_in_oil_mass_rate(oil_mass_rate)
        oil_after.set_liquid_flow_rate("oil", oil_mass_rate)
        oil_after.set_liquid_flow_rate("H2O", water_in_oil_mass_rate)
        oil_after.set_temperature_and_pressure(temperature_outlet, pressure_outlet)

        water_density_STP = rho("H2O", std_temp, std_press, PHASE_LIQUID)
        water_mass_rate = (oil_volume_rate * water_oil_ratio * water_density_STP.to("tonne/barrel_water") -
                           water_in_oil_mass_rate)
        water_after = self.find_output_stream("water")
        water_after.set_liquid_flow_rate("H2O", water_mass_rate)
        water_after.set_temperature_and_pressure(temperature_outlet, pressure_outlet)
        return gas_after, oil_after, water_after

    def water_in_oil_mass_rate(self, oil_mass_rate):
        """

        :param field:
        :param oil_mass_rate: (float) oil mass rate
        :return: (float) water mass rate in the oil stream after separation (unit = tonne/day)
        """
        water_content = self.attr("water_content_oil_emulsion")
        water_in_oil_mass_rate = (oil_mass_rate * water_content).to("tonne/day")
        return water_in_oil_mass_rate

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

    def compressor_brake_horsepower_of_stages(self, field, gas_stream, gas_compression_volume_stages):
        """
        Get the compressor horsepower of all stages in the separator

        :param field:
        :param gas_stream:
        :param gas_compression_volume_stages: (float) a list contains gas compression volume for each stages
        :return: (float) compresssor brake horsepower for each stages
        """

        num_of_stages = self.attr("number_stages")
        temperature_of_stages, pressure_of_stages = self.get_stages_temperature_and_pressure(field)
        pressure_after_boosting = self.attr("gas_pressure_after_boosting")
        compressor_eff = self.attr("eta_compressor").to("frac")

        overall_compression_ratio_stages = [pressure_after_boosting /
                                            pressure_of_stages[stage] for stage in range(num_of_stages)]
        compression_ratio_per_stages = get_compression_ratio_stages(overall_compression_ratio_stages)
        num_of_compression_stages = get_num_of_compression_stages(overall_compression_ratio_stages,
                                                                  compression_ratio_per_stages)  # (int)

        brake_horsepower_of_stages = []
        for (inlet_temp, inlet_press, compression_ratio,
             gas_compression_volume, num_of_compression) \
                in zip(temperature_of_stages,
                       pressure_of_stages,
                       compression_ratio_per_stages,
                       gas_compression_volume_stages,
                       num_of_compression_stages):
            work_sum = Compressor.get_compressor_work(field, inlet_temp, inlet_press,
                                                      gas_stream, compression_ratio, num_of_compression)
            horsepower = work_sum * gas_compression_volume
            brake_horsepower = horsepower / compressor_eff
            brake_horsepower_of_stages.append(brake_horsepower)

        return brake_horsepower_of_stages
