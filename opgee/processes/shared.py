#
# Functions used by Process subclasses
#
# Author: Wennan Long
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .. import ureg
from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL, EN_RESID
from ..error import OpgeeException
from ..stream import Stream, PHASE_GAS

_slope = {"NG_engine": -0.6035,
          "NG_turbine": -0.1279}

_intercept = {"NG_engine": 7922.4,
              "NG_turbine": 9219.6}

_maxBHP = {"NG_engine": 2800.0,
           "Diesel_engine": 3000.0,
           "NG_turbine": 21000.0,
           "Electric_motor": 1000.0}


def get_efficiency(prime_mover_type, brake_horsepower):
    """

    :param prime_mover_type:
    :param brake_horsepower:
    :return: (pint.Quantity) efficiency in units of "btu/horsepower/hour"
    """
    brake_horsepower = brake_horsepower.to("horsepower").m
    brake_horsepower = min(_maxBHP[prime_mover_type], brake_horsepower)

    if prime_mover_type == "Electric_motor":
        efficiency = 2967 * brake_horsepower ** (-0.018) if brake_horsepower != 0.0 else 3038
    elif prime_mover_type == "Diesel_engine":
        efficiency = 0.0004 * brake_horsepower ** 2 - 1.6298 * brake_horsepower + 7955.8
    else:
        efficiency = _slope[prime_mover_type] * brake_horsepower + _intercept[prime_mover_type]

    return ureg.Quantity(efficiency, "btu/horsepower/hour")


def get_init_lifting_stream(gas,
                            lifting_gas_stream,
                            gas_lifting_vol_rate):
    """
    Generate initial gas stream for lifting

    :param gas_lifting_vol_rate: GLIR * (oil rate + water rate)
    :param lifting_gas_stream: (Stream) stream that used for gas lifting
    :param gas: (Gas) the current Field's ``Gas`` instance
    :return: (Stream) initial gas lifting stream
    """

    lifting_gas_mass_fracs = gas.component_mass_fractions(gas.component_molar_fractions(lifting_gas_stream))

    series = (lifting_gas_mass_fracs *
              gas_lifting_vol_rate *
              gas.component_gas_rho_STP[lifting_gas_stream.gas_flow_rates().index])

    stream = Stream("gas lifting stream", lifting_gas_stream.tp)
    stream.set_rates_from_series(series, PHASE_GAS)
    stream.set_tp(lifting_gas_stream.tp)
    return stream


#
# Helper function shared by acid_gas_removal and demethanizer
#
def predict_blower_energy_use(proc, thermal_load, air_cooler_delta_T=None, water_press=None,
                              air_cooler_fan_eff=None, air_cooler_speed_reducer_eff=None):
    """
    Predict blower energy use per day. Any parameters not explicitly provided are taken
    from the `proc` object.

    :param thermal_load: (float) thermal load (unit = btu/hr)
    :param air_cooler_delta_T:
    :param water_press:
    :param air_cooler_fan_eff:
    :param air_cooler_speed_reducer_eff:
    :return: (pint.Quantity) air cooling fan energy consumption (unit = "kWh/day")
    """

    def _value(value, dflt):
        return (dflt if value is None else value)

    air_cooler_delta_T = _value(air_cooler_delta_T, proc.air_cooler_delta_T)
    water_press = _value(water_press, proc.water_press)
    air_cooler_fan_eff = _value(air_cooler_fan_eff, proc.air_cooler_fan_eff)
    air_cooler_speed_reducer_eff = _value(air_cooler_speed_reducer_eff, proc.air_cooler_speed_reducer_eff)

    model = proc.field.model
    blower_air_quantity = thermal_load / model.const("air-elevation-corr") / air_cooler_delta_T
    blower_CFM = blower_air_quantity / model.const("air-density-ratio")
    blower_delivered_hp = blower_CFM * water_press / air_cooler_fan_eff
    blower_fan_motor_hp = blower_delivered_hp / air_cooler_speed_reducer_eff
    air_cooler_energy_consumption = get_energy_consumption("Electric_motor", blower_fan_motor_hp)
    return air_cooler_energy_consumption.to("kWh/day")


def get_energy_carrier(prime_mover_type):
    if prime_mover_type.startswith("NG_") or prime_mover_type.lower() == "natural gas":
        return EN_NATURAL_GAS

    if prime_mover_type.startswith("Electric"):
        return EN_ELECTRICITY

    if prime_mover_type.startswith("Diesel"):
        return EN_DIESEL

    if prime_mover_type.startswith("Resid"):
        return EN_RESID

    raise OpgeeException(f"Unrecognized prime_mover_type: '{prime_mover_type}'")


def get_energy_consumption_stages(prime_mover_type, brake_horsepower_of_stages):
    energy_consumption_of_stages = []
    for brake_horsepower in brake_horsepower_of_stages:
        eff = get_efficiency(prime_mover_type, brake_horsepower)
        energy_consumption = (brake_horsepower * eff).to("mmBtu/day")
        energy_consumption_of_stages.append(energy_consumption)

    return energy_consumption_of_stages


def get_energy_consumption(prime_mover_type, brake_horsepower):
    eff = get_efficiency(prime_mover_type, brake_horsepower)
    energy_consumption = (brake_horsepower * eff).to("mmBtu/day")

    return energy_consumption


def get_bounded_value(value, name, variable_bound_dict):
    """

    :param value:
    :param name:
    :param variable_bound_dict: dictionary of bounded variables; key = variable name (str), value = [min, max]
    :return: bounded valued without unit
    """
    try:
        bounds = variable_bound_dict[name]
    except KeyError:
        raise OpgeeException(f"Variable bound dictionary does not have {name}")

    return min(max(value, bounds[0]), bounds[1])
