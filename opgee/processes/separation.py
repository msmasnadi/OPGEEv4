from ..combine_streams import combine_streams
from ..log import getLogger
from ..process import Process

from ..energy import Energy, EN_NATURAL_GAS, EN_ELECTRICITY
from .. import ureg
from ..stream import Stream, PHASE_GAS, PHASE_LIQUID, PHASE_SOLID
from ..thermodynamics import rho
from ..compressor import Compressor
from ..emissions import EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES

_logger = getLogger(__name__)


class Separation(Process):
    def _after_init(self):
        super()._after_init()
        self.field = field = self.get_field()
        self.oil_volume_rate = field.attr("oil_prod")

        # Primary mover type is one of: {"NG_engine", "Electric_motor", "Diesel_engine", "NG_turbine"}
        self.prime_mover_type = self.attr("prime_mover_type")

        self.wellhead_temp = field.attr("wellhead_temperature")
        self.wellhead_press = field.attr("wellhead_pressure")
        self.loss_rate = self.venting_fugitive_rate()
        self.loss_rate = (1 / (1 - self.loss_rate)).to("frac")
        self.temperature_outlet = field.attr("temperature_outlet")
        self.temperature_stage1 = field.attr("wellhead_temperature")
        self.temperature_stage2 = (self.temperature_stage1.to("kelvin") + self.temperature_outlet.to("kelvin")) / 2
        self.pressure_stage1 = self.attr("pressure_first_stage")
        self.pressure_stage2 = self.attr("pressure_second_stage")
        self.pressure_stage3 = self.attr("pressure_third_stage")
        self.oil_volume_rate = field.attr("oil_prod")  # (float) bbl/day
        self.gas_oil_ratio = field.attr("GOR")  # (float) scf/bbl
        self.gas_comp = field.attrs_with_prefix("gas_comp_")  # Pandas.Series (float) percent

        self.water_oil_ratio = field.attr("WOR")

        self.num_of_stages = self.attr("number_stages")

        self.std_temp = field.model.const("std-temperature")
        self.std_press = field.model.const("std-pressure")
        self.pressure_after_boosting = field.attr("gas_pressure_after_boosting")
        self.pressure_outlet = field.attr("pressure_outlet")

        self.water_content = self.attr("water_content_oil_emulsion")
        self.compressor_eff = field.attr("eta_compressor").to("frac")

    def run(self, analysis):
        self.print_running_msg()

        # mass rate
        input = self.find_input_stream("crude oil")

        loss_rate = self.venting_fugitive_rate()
        gas_fugitives_temp = self.set_gas_fugitives(input, loss_rate)
        gas_fugitives = self.find_output_stream("gas fugitives")
        gas_fugitives.copy_flow_rates_from(gas_fugitives_temp)

        gas_after = self.find_output_stream("gas")
        # Check
        self.set_iteration_value(gas_after.total_flow_rate())
        gas_after.copy_gas_rates_from(input)
        gas_after.subtract_gas_rates_from(gas_fugitives)

        # energy rate

        free_gas_stages, final_SOR = self.get_free_gas_stages(self.field)  # (float, list) scf/bbl
        gas_compression_volume_stages = [(self.oil_volume_rate * free_gas).to("mmscf/day") for free_gas in free_gas_stages]
        compressor_brake_horsepower_of_stages = self.compressor_brake_horsepower_of_stages(self.field,
                                                                                           gas_after,
                                                                                           gas_compression_volume_stages)
        energy_consumption_of_stages = self.get_energy_consumption_stages(self.prime_mover_type,
                                                                          compressor_brake_horsepower_of_stages)
        energy_consumption_sum = sum(energy_consumption_of_stages)

        energy_use = self.energy
        energy_carrier = EN_NATURAL_GAS if self.prime_mover_type == "NG_engine" else EN_ELECTRICITY
        energy_use.set_rate(energy_carrier, energy_consumption_sum)

        # emission rate
        emissions = self.emissions
        energy_for_combustion = energy_use.data.drop("Electricity")
        combustion_emission = (energy_for_combustion * self.process_EF).sum()
        emissions.add_rate(EM_COMBUSTION, "CO2", combustion_emission)

        emissions.add_from_stream(EM_FUGITIVES, gas_fugitives)

    def impute(self):
        oil = self.field.oil

        gas_after, oil_after, water_after = self.get_output_streams(self.field)
        gas_after.multiply_flow_rates(self.loss_rate)

        output = combine_streams([oil_after, gas_after, water_after], oil.API, self.wellhead_press)

        input = self.find_input_stream("crude oil")
        input.set_temperature_and_pressure(self.wellhead_temp, self.wellhead_press)
        input.copy_flow_rates_from(output)

    def get_stages_temperature_and_pressure(self):

        temperature_of_stages = [self.temperature_stage1, self.temperature_stage2.to("degF"), self.temperature_outlet]

        pressure_of_stages = [self.pressure_stage1, self.pressure_stage2, self.pressure_stage3]

        return temperature_of_stages, pressure_of_stages

    def get_output_streams(self, field):
        temperature_of_stages, pressure_of_stages = self.get_stages_temperature_and_pressure()

        oil = field.oil
        gas = field.gas

        gas_after = self.find_output_stream("gas")
        stream = Stream("stage_stream",
                        temperature=temperature_of_stages[self.num_of_stages - 1],
                        pressure=pressure_of_stages[self.num_of_stages - 1])

        density = oil.density(stream,  # lb/ft3
                              oil.oil_specific_gravity,
                              oil.gas_specific_gravity,
                              oil.gas_oil_ratio)

        gas_volume_rate = self.oil_volume_rate * self.gas_oil_ratio * self.gas_comp
        gas_density = gas.component_gas_rho_STP[self.gas_comp.index]
        gas_mass_rate = gas_volume_rate * gas_density

        for component, mass_rate in gas_mass_rate.items():
            gas_after.set_gas_flow_rate(component, mass_rate.to("tonne/day"))
        gas_after.set_temperature_and_pressure(self.temperature_outlet, self.pressure_after_boosting)

        oil_after = self.find_output_stream("crude oil")
        oil_mass_rate = (self.oil_volume_rate * density).to("tonne/day")
        water_in_oil_mass_rate = self.water_in_oil_mass_rate(oil_mass_rate)
        oil_after.set_liquid_flow_rate("oil", oil_mass_rate)
        oil_after.set_liquid_flow_rate("H2O", water_in_oil_mass_rate)
        oil_after.set_temperature_and_pressure(self.temperature_outlet, self.pressure_outlet)

        water_density_STP = rho("H2O", self.std_temp, self.std_press, PHASE_LIQUID)
        water_mass_rate = (self.oil_volume_rate * self.water_oil_ratio * water_density_STP.to("tonne/barrel_water") -
                           water_in_oil_mass_rate)
        water_after = self.find_output_stream("water")
        water_after.set_liquid_flow_rate("H2O", water_mass_rate)
        water_after.set_temperature_and_pressure(self.temperature_outlet, self.pressure_outlet)
        return gas_after, oil_after, water_after

    def water_in_oil_mass_rate(self, oil_mass_rate):
        """

        :param field:
        :param oil_mass_rate: (float) oil mass rate
        :return: (float) water mass rate in the oil stream after separation (unit = tonne/day)
        """
        water_in_oil_mass_rate = (oil_mass_rate * self.water_content).to("tonne/day")
        return water_in_oil_mass_rate

    def get_free_gas_stages(self, field):
        oil = field.oil

        temperature_of_stages, pressure_of_stages = self.get_stages_temperature_and_pressure()

        solution_gas_oil_ratio_of_stages = [oil.gas_oil_ratio]
        for stage in range(self.num_of_stages):
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

        return free_gas_of_stages, solution_gas_oil_ratio_of_stages[-1]

    def compressor_brake_horsepower_of_stages(self, field, gas_stream, gas_compression_volume_stages):
        """
        Get the compressor horsepower of all stages in the separator

        :param field:
        :param gas_stream:
        :param gas_compression_volume_stages: (float) a list contains gas compression volume for each stages
        :return: (float) compresssor brake horsepower for each stages
        """

        temperature_of_stages, pressure_of_stages = self.get_stages_temperature_and_pressure()

        overall_compression_ratio_stages = [self.pressure_after_boosting /
                                            pressure_of_stages[stage] for stage in range(self.num_of_stages)]
        compression_ratio_per_stages = Compressor.get_compression_ratio_stages(overall_compression_ratio_stages)
        num_of_compression_stages = Compressor.get_num_of_compression_stages(overall_compression_ratio_stages)  # (int)

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
            brake_horsepower = horsepower / self.compressor_eff
            brake_horsepower_of_stages.append(brake_horsepower)

        return brake_horsepower_of_stages
