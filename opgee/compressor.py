from opgee.core import OpgeeObject
import numpy as np
from thermosteam import Chemical, Mixture
from opgee.stream import PHASE_LIQUID, Stream, PHASE_GAS, PHASE_SOLID
from opgee import ureg


class Compressor(OpgeeObject):

    def __init__(self, field):
        self.field = field

    @staticmethod
    def get_compressor_work(field, inlet_temp, inlet_press, gas_stream, compression_ratio, num_of_compression):

        gas = field.gas

        for j in range(num_of_compression):
            corrected_temp = gas.corrected_pseudocritical_temperature(gas_stream)
            corrected_press = gas.corrected_pseudocritical_pressure(gas_stream)
            inlet_reduced_temp = inlet_temp.to("rankine") / corrected_temp
            inlet_reduced_press = inlet_press / corrected_press
            z_factor = gas.Z_factor(inlet_reduced_temp, inlet_reduced_press)
            ratio_of_specific_heat = gas.ratio_of_specific_heat(gas_stream)
            work = 0

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
        return work_sum