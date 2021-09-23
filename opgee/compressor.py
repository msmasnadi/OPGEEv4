from opgee.core import OpgeeObject
from opgee import ureg
from .error import OpgeeException, AbstractMethodError, OpgeeStopIteration

_power = [1, 1 / 2, 1 / 3, 1 / 4, 1 / 5]


class Compressor(OpgeeObject):

    def __init__(self, field):
        self.field = field

    @staticmethod
    def get_compressor_work_temp(field, inlet_temp, inlet_press, gas_stream, compression_ratio, num_of_compression):
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
        return work_sum, inlet_temp

    @staticmethod
    def get_compression_ratio_stages(overall_compression_ratio_stages):
        max_stages = len(_power)
        compression_ratio_per_stages = []

        for compression_ratio in overall_compression_ratio_stages:
            if compression_ratio < 1:
                raise OpgeeException("compression ratio is less than 1")
            for pow in _power:
                if compression_ratio ** pow < max_stages:
                    compression_ratio_per_stages.append(compression_ratio ** pow)
                    break

        return compression_ratio_per_stages

    @staticmethod
    def get_compression_ratio(overall_compression_ratio):
        if overall_compression_ratio < 1:
            raise OpgeeException("compression ratio is less than 1")
        max_stages = len(_power)
        result = 0

        for pow in _power:
            if overall_compression_ratio ** pow < max_stages:
                result = overall_compression_ratio ** pow
                return result

    @staticmethod
    def get_num_of_compression_stages(overall_compression_ratio_stages):
        num_of_compression_stages = []
        compression_ratio_per_stages = Compressor.get_compression_ratio_stages(overall_compression_ratio_stages)

        for overall_compression_ratio, compression_ratio in \
                zip(overall_compression_ratio_stages, compression_ratio_per_stages):
            if overall_compression_ratio < 1:
                raise OpgeeException("compression ratio is less than 1")
            for pow in _power:
                if overall_compression_ratio ** pow == compression_ratio:
                    num_of_compression_stages.append(int(1 / pow))
                    break

        return num_of_compression_stages

    @staticmethod
    def get_num_of_compression(overall_compression_ratio):
        if overall_compression_ratio < 1:
            raise OpgeeException("compression ratio is less than 1")
        result = 0
        compression_ratio = Compressor.get_compression_ratio(overall_compression_ratio)

        for pow in _power:
            if overall_compression_ratio ** pow == compression_ratio:
                result = int(1 / pow)
                return result

