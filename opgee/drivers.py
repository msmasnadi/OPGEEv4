#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from . import ureg

_slope = {"NG_engine": -0.6035,
          "Diesel_engine": -0.4299,
          "NG_turbine": -0.1279}

_intercept = {"NG_engine": 7922.4,
              "Diesel_engine": 7235.4,
              "NG_turbine": 9219.6}

def get_efficiency(prime_mover_type, brake_horsepower):
    """

    :param prime_mover_type:
    :param brake_horsepower:
    :return: (pint.Quantity) efficiency in units of "btu/horsepower/hour"
    """
    brake_horsepower = brake_horsepower.to("horsepower")

    if prime_mover_type == "Electric_motor":
        efficiency = 2967 * brake_horsepower.m ** (-0.018) if brake_horsepower != 0.0 else 3038
    else:
        efficiency = _slope[prime_mover_type] * brake_horsepower.m + _intercept[prime_mover_type]

    efficiency = max(efficiency, 6000)
    return ureg.Quantity(efficiency, "btu/horsepower/hour")
