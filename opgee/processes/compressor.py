#
# Compressor class
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from typing import Optional, Sequence, Tuple

from pint.facets.plain import PlainQuantity as Quantity

from opgee.core import OpgeeObject, TemperaturePressure
from opgee.processes.shared import get_energy_consumption
from opgee.stream import Stream
from opgee.units import ureg

# type aliases
Q_Float = Quantity[float]
Q_IntTuple = Tuple[Q_Float, int]



_power = [1, 1 / 2, 1 / 3, 1 / 4, 1 / 5]

class Compressor(OpgeeObject):
    def __init__(self, field):
        self.field = field

    @staticmethod
    def get_compressor_work_temp(field, inlet_temp, inlet_press, gas_stream, compression_ratio, num_of_compression,
    ) -> Tuple[Q_Float, Q_Float, Q_Float]:
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
        work_temp1: Quantity = 3.027 * 14.7 / (60 + 460) * ratio_of_specific_heat / (ratio_of_specific_heat - 1)
        ratio = (ratio_of_specific_heat - 1) / ratio_of_specific_heat
        work: Quantity = ureg.Quantity(0.0, "frac * rankine")
        for _ in range(num_of_compression):
            inlet_reduced_temp = inlet_temp.to("rankine") / corrected_temp
            inlet_reduced_press = inlet_press / corrected_press
            z_factor = gas.Z_factor(inlet_reduced_temp, inlet_reduced_press)

            work_temp2 = (compression_ratio ** z_factor) ** ratio - 1
            work += work_temp1 * work_temp2 * inlet_temp.to("rankine")

            delta_temp = (inlet_temp.to("rankine") * compression_ratio ** (z_factor * ratio) - inlet_temp) * 0.2
            inlet_temp = ureg.Quantity(inlet_temp.m + delta_temp.m, "degF")
            inlet_press = compression_ratio * inlet_press

        work_sum = ureg.Quantity(work.m, "hp*day/mmscf")
        return work_sum, inlet_temp, inlet_press

    @staticmethod
    def get_compression_ratio_stages(
        overall_compression_ratio_stages: Sequence[Q_Float]
    ) -> Sequence[Q_IntTuple]:
        compression_ratios: map[Optional[Q_IntTuple]] = map(
            Compressor.get_compression_ratio_and_stage, overall_compression_ratio_stages
        )
        return [ratio for ratio in compression_ratios if ratio is not None]

    @staticmethod
    @ureg.wraps(("frac", None), "frac", strict=False)
    def get_compression_ratio_and_stage(overall_compression_ratio: float) -> Optional[Q_IntTuple]:
        max_stages = len(_power)
        for pow in _power:
            comp_raised = overall_compression_ratio ** pow
            if comp_raised < max_stages:
                return comp_raised, int(1 / pow)

    @staticmethod
    @ureg.wraps(("mmbtu/day", "degF", "psia"), (None, None, None, "frac", None, None))
    def get_compressor_energy_consumption(
        field,
        prime_mover_type,
        eta_compressor,
        overall_compression_ratio,
        inlet_stream: Stream,
        inlet_tp: Optional[TemperaturePressure] = None,
    ):
        """
        Calculate compressor energy consumption

        :param field: (Field)
        :param prime_mover_type:
        :param eta_compressor:
        :param overall_compression_ratio:
        :param inlet_stream: (Stream)
        :param inlet_tp: (TemperaturePressure) the T and P at the inlet to override
           that in the inlet_stream
        :return:
        """
        energy_consumption = ureg.Quantity(0, "mmbtu/day")
        tp: TemperaturePressure = inlet_tp or inlet_stream.tp
        inlet_temp, inlet_press = tp.get()

        if overall_compression_ratio < 1 or inlet_stream.has_zero_flow():
            return energy_consumption, inlet_temp, inlet_press

        compression_ratio, num_stages = Compressor.get_compression_ratio_and_stage(overall_compression_ratio)
        total_work, outlet_temp, outlet_press = Compressor.get_compressor_work_temp(field,
                                                                                    inlet_temp,
                                                                                    inlet_press,
                                                                                    inlet_stream,
                                                                                    compression_ratio,
                                                                                    num_stages)
        volume_flow_rate_STP = field.gas.volume_flow_rate_STP(inlet_stream)
        total_energy = total_work * volume_flow_rate_STP
        brake_horse_power = total_energy / eta_compressor
        energy_consumption = get_energy_consumption(prime_mover_type, brake_horse_power)

        return energy_consumption, outlet_temp, outlet_press
