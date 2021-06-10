from opgee.core import OpgeeObject
from opgee import ureg


class Compressor(OpgeeObject):

    def __init__(self, field):
        self.field = field

    @staticmethod
    def get_compressor_work(field, inlet_temp, inlet_press, gas_stream, compression_ratio, num_of_compression):
        """

        :param field:
        :param inlet_temp:
        :param inlet_press:
        :param gas_stream:
        :param compression_ratio:
        :param num_of_compression:
        :return:(float) overall work from compressor which has maximum five stages (unit = hp*day/mmscf)
        """
        gas = field.gas
        corrected_temp = gas.corrected_pseudocritical_temperature(gas_stream)
        corrected_press = gas.corrected_pseudocritical_pressure(gas_stream)
        ratio_of_specific_heat = gas.ratio_of_specific_heat(gas_stream)
        work_temp1 = 3.027 * 14.7 / (60 + 460) * ratio_of_specific_heat / (ratio_of_specific_heat - 1)
        ratio = (ratio_of_specific_heat - 1) / ratio_of_specific_heat
        work = 0
        for j in range(num_of_compression):
            inlet_reduced_temp = inlet_temp.to("rankine") / corrected_temp
            inlet_reduced_press = inlet_press / corrected_press
            z_factor = gas.Z_factor(inlet_reduced_temp, inlet_reduced_press)

            work_temp2 = (compression_ratio ** z_factor) ** ratio - 1
            work += work_temp1 * work_temp2 * inlet_temp.to("rankine")

            delta_temp = (inlet_temp.to("rankine") * compression_ratio ** (z_factor * ratio) - inlet_temp) * 0.2
            inlet_temp = ureg.Quantity(inlet_temp.m + delta_temp.m, "degF")
            inlet_press = (compression_ratio * inlet_press if j == 0 else
                           inlet_press * compression_ratio * num_of_compression)

        work_sum = ureg.Quantity(work.m, "hp*day/mmscf")
        return work_sum
