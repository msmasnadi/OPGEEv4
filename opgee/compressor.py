from opgee.core import OpgeeObject
import numpy as np
from thermosteam import Chemical, Mixture
from opgee.stream import PHASE_LIQUID, Stream, PHASE_GAS, PHASE_SOLID
from opgee import ureg


class Compressor(OpgeeObject):
    power = [1, 1 / 2, 1 / 3, 1 / 4, 1 / 5]

    def __init__(self, field):
        self.field = field

    def get_compression_ratio_stages(self, overall_compression_ratio_stages):
        max_stages = len(self.power)
        compression_ratio_per_stages = []

        for compression_ratio in overall_compression_ratio_stages:
            for pow in self.power:
                if compression_ratio ** pow < max_stages:
                    compression_ratio_per_stages.append(compression_ratio ** pow)
                    break

        return compression_ratio_per_stages

    def get_num_of_compression_stages(self, overall_compression_ratio_stages, compression_ratio_per_stages):
        num_of_compression_stages = []

        for overall_compression_ratio, compression_ratio in \
                zip(overall_compression_ratio_stages, compression_ratio_per_stages):
            for pow in self.power:
                if overall_compression_ratio ** pow == compression_ratio:
                    num_of_compression_stages.append(int(1 / pow))
                    break

        return num_of_compression_stages

    def compressor_horsepower_of_stages(self, gas_stream):
        gas = self.field.gas

        # num_of_stages = field.attr("number_stages")
        # temperature_of_stages, pressure_of_stages = self.get_stages_temperature_and_pressure(field)
        # pressure_after_boosting = self.attr("gas_pressure_after_boosting")

        # overall_compression_ratio_stages = [pressure_after_boosting /
        #                                     pressure_of_stages[stage] for stage in range(num_of_stages)]
        # compression_ratio_per_stages = get_compression_ratio_stages(overall_compression_ratio_stages)
        num_of_compression_stages = self.get_num_of_compression_stages(overall_compression_ratio_stages,
                                                                  compression_ratio_per_stages)  # (int)

        # horsepower_of_stages = []
        # for (inlet_temp, inlet_press, compression_ratio,
        #      gas_compression_volume, num_of_compression) \
        #         in zip(temperature_of_stages,
        #                pressure_of_stages,
        #                compression_ratio_per_stages,
        #                gas_compression_volume_stages,
        #                num_of_compression_stages):
        #     work = 0


        # for j in range(num_of_compression):
        #     inlet_temp = gas_stream.temperature
        #     inlet_press = gas_stream.pressure
        #     inlet_reduced_temp = inlet_temp.to("rankine") / gas.corrected_pseudocritical_temperature(gas_stream)
        #     inlet_reduced_press = inlet_press / gas.corrected_pseudocritical_pressure(gas_stream)
        #     z_factor = gas.Z_factor(inlet_reduced_temp, inlet_reduced_press)
        #     ratio_of_specific_heat = gas.ratio_of_specific_heat(gas_stream)
        #
        #     work_temp1 = 3.027 * 14.7 / (60 + 460) * ratio_of_specific_heat / (ratio_of_specific_heat - 1)
        #     ratio = (ratio_of_specific_heat - 1) / ratio_of_specific_heat
        #     work_temp2 = (compression_ratio ** z_factor) ** ratio - 1
        #     work += work_temp1 * work_temp2 * inlet_temp.to("rankine")
        #
        #     delta_temp = (inlet_temp.to("rankine") *
        #                   compression_ratio ** (z_factor * ratio) - inlet_temp) * 0.2
        #     inlet_temp = ureg.Quantity(inlet_temp.m + delta_temp.m, "degF")
        #     inlet_press = (compression_ratio * inlet_press if j == 0 else
        #                    inlet_press * compression_ratio * num_of_compression)
        #
        # work_sum = ureg.Quantity(work.m, "hp*day/mmscf")
        # horsepower = work_sum * gas_compression_volume
        # horsepower_of_stages.append(horsepower)
        #
        # return horsepower_of_stages
