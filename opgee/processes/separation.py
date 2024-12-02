#
# Separation class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..combine_streams import combine_streams
from ..core import TemperaturePressure
from ..emissions import EM_FUGITIVES
from ..log import getLogger
from ..process import Process
from ..processes.compressor import Compressor
from ..stream import Stream, PHASE_GAS
from .shared import get_energy_carrier, get_energy_consumption_stages

_logger = getLogger(__name__)


class Separation(Process):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        # TODO: avoid process names in contents.
        self._required_inputs = [
            "oil",
        ]

        self._required_outputs = [
            "gas for partition",    # TODO: this is called "gas for gas partition" elsewhere
        ]

        self.compressor_eff = None
        self.gas_comp = None
        self.gas_oil_ratio = None
        self.loss_rate = None
        self.loss_rate = None
        self.num_of_stages = None
        self.num_of_stages = None
        self.oil_volume_rate = None
        self.outlet_tp = None
        self.pressure_after_boosting = None
        self.pressure_stage1 = None
        self.pressure_stage2 = None
        self.pressure_stage3 = None
        self.prime_mover_type = None
        self.temperature_stage1 = None
        self.temperature_stage2 = None
        self.water_content = None

        self.cache_attributes()

    def cache_attributes(self):
        field = self.field
        self.oil_volume_rate = field.oil_volume_rate

        # Primary mover type is one of: {"NG_engine", "Electric_motor", "Diesel_engine", "NG_turbine"}
        self.prime_mover_type = self.attr("prime_mover_type")

        self.loss_rate = self.venting_fugitive_rate()
        self.loss_rate = (1 / (1 - self.loss_rate)).to("frac")

        self.outlet_tp = TemperaturePressure(self.attr("temperature_outlet"),
                                             self.attr("pressure_outlet"))

        self.temperature_stage1 = field.wellhead_t
        self.temperature_stage2 = (self.temperature_stage1.to("kelvin") + self.outlet_tp.T.to("kelvin")) / 2

        #TODO: move it to smart default
        self.pressure_stage1 = min(field.wellhead_p, self.attr("pressure_first_stage"))
        self.pressure_stage2 = self.attr("pressure_second_stage")
        self.pressure_stage3 = self.attr("pressure_third_stage")

        self.gas_oil_ratio = field.gas_oil_ratio
        self.gas_comp = field.gas_comp

        self.num_of_stages = self.attr("number_stages")
        #TODO: move it to smart default
        if field.wellhead_p.m < 500:
            self.num_of_stages = 1

        self.pressure_after_boosting = field.stab_gas_press

        self.water_content = self.attr("water_content_oil_emulsion")
        self.compressor_eff = self.attr("eta_compressor")

    def run(self, analysis):
        self.print_running_msg()
        field = self.field

        #TODO: Fix this after data pipeline is done
        water_oil_ratio = field.attr("WOR")

        # mass rate
        input = self.find_input_stream("oil")

        loss_rate = field.component_fugitive_table[self.name]
        gas_fugitives = self.set_gas_fugitives(input, loss_rate)

        gas_after = self.find_output_stream("gas for partition")
        gas_after.copy_gas_rates_from(input)
        gas_after.subtract_rates_from(gas_fugitives)
        field.save_process_data(gas_tp_after_separation=gas_after.tp)

        self.set_iteration_value(gas_after.total_flow_rate())

        # energy rate

        free_gas_stages, final_GOR = self.get_free_gas_stages(field, input)  # (float, list) scf/bbl
        gas_compression_volume_stages = [(self.oil_volume_rate * free_gas).to("mmscf/day") for free_gas in
                                         free_gas_stages]
        compressor_brake_horsepower_of_stages = self.compressor_brake_horsepower_of_stages(self.field,
                                                                                           gas_after,
                                                                                           gas_compression_volume_stages)
        energy_consumption_of_stages = get_energy_consumption_stages(self.prime_mover_type,
                                                                     compressor_brake_horsepower_of_stages)
        energy_consumption_sum = sum(energy_consumption_of_stages)

        energy_use = self.energy
        energy_carrier = get_energy_carrier(self.prime_mover_type)
        energy_use.set_rate(energy_carrier, energy_consumption_sum)

        # import/export
        self.set_import_from_energy(energy_use)

        # emission rate
        self.set_combustion_emissions()
        self.emissions.set_from_stream(EM_FUGITIVES, gas_fugitives)

    def impute(self):
        field = self.field
        oil = field.oil

        gas_after, oil_after, water_after = self.get_output_streams(field)
        output = combine_streams([oil_after, gas_after, water_after])

        loss_rate = field.component_fugitive_table[self.name]
        loss_rate = (1 / (1 - loss_rate)).to("frac")
        output.multiply_flow_rates(loss_rate)

        input = self.find_input_stream("oil")
        input.copy_flow_rates_from(output, tp=field.wellhead_tp)
        oil_LHV_rate = oil.energy_flow_rate(input)
        gas_LHV_rate = field.gas.energy_flow_rate(input)
        field.save_process_data(wellhead_LHV_rate=gas_LHV_rate + oil_LHV_rate)

    def get_stages_temperature_and_pressure(self):

        temperature_of_stages = [self.temperature_stage1, self.temperature_stage2.to("degF"), self.outlet_tp.T]

        pressure_of_stages = [self.pressure_stage1, self.pressure_stage2, self.pressure_stage3]

        return temperature_of_stages, pressure_of_stages

    def get_output_streams(self, field):
        temperature_of_stages, pressure_of_stages = self.get_stages_temperature_and_pressure()

        oil = field.oil
        gas = field.gas

        gas_after = self.find_output_stream("gas for partition")

        last = self.num_of_stages - 1
        stream = Stream("stage_stream", TemperaturePressure(temperature_of_stages[last],
                                                            pressure_of_stages[last]))

        density = oil.density(stream,  # lb/ft3
                              oil.oil_specific_gravity,
                              oil.gas_specific_gravity,
                              oil.gas_oil_ratio)

        gas_volume_rate = self.oil_volume_rate * self.gas_oil_ratio * self.gas_comp
        gas_density = gas.component_gas_rho_STP[self.gas_comp.index]
        gas_mass_rate = gas_volume_rate * gas_density
        gas_after.set_rates_from_series(gas_mass_rate, PHASE_GAS)
        gas_after.tp.set(T=self.outlet_tp.T, P=self.pressure_after_boosting)

        oil_after = self.find_output_stream("oil")
        oil_mass_rate = (self.oil_volume_rate * density).to("tonne/day")
        water_in_oil_mass_rate = self.water_in_oil_mass_rate(oil_mass_rate)
        oil_after.set_liquid_flow_rate("oil", oil_mass_rate)
        oil_after.set_liquid_flow_rate("H2O", water_in_oil_mass_rate)
        oil_after.set_tp(self.outlet_tp)
        oil_after.set_API(field.attr("API"))

        water_density_STP = field.water.density()
        water_mass_rate = max(0, self.oil_volume_rate * field.attr("WOR") * water_density_STP - water_in_oil_mass_rate)
        water_after = self.find_output_stream("water")
        water_after.set_liquid_flow_rate("H2O", water_mass_rate, tp=self.outlet_tp)

        return gas_after, oil_after, water_after

    def water_in_oil_mass_rate(self, oil_mass_rate):
        """

        :param field:
        :param oil_mass_rate: (float) oil mass rate
        :return: (float) water mass rate in the oil stream after separation (unit = tonne/day)
        """
        water_in_oil_mass_rate = (oil_mass_rate * self.water_content).to("tonne/day")
        return water_in_oil_mass_rate

    def get_free_gas_stages(self, field, input_stream):
        oil = field.oil

        temperature_of_stages, pressure_of_stages = self.get_stages_temperature_and_pressure()

        solution_gas_oil_ratio_of_stages = [oil.gas_oil_ratio]
        oil_SG = oil.specific_gravity(input_stream.API)
        for stage in range(self.num_of_stages):
            stream_stages = Stream("stage_stream", TemperaturePressure(temperature_of_stages[stage],
                                                                       pressure_of_stages[stage]))
            solution_gas_oil_ratio = oil.solution_gas_oil_ratio(stream_stages,
                                                                oil_SG,
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
            work_sum, _, _ = Compressor.get_compressor_work_temp(field, inlet_temp, inlet_press,
                                                                 gas_stream, compression_ratio, num_of_compression)
            horsepower = work_sum * gas_compression_volume
            brake_horsepower = horsepower / self.compressor_eff
            brake_horsepower_of_stages.append(brake_horsepower)

        return brake_horsepower_of_stages
