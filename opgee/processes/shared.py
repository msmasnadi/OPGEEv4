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


def get_gas_lifting_init_stream(gas,
                                imported_fuel_gas_comp,
                                imported_fuel_gas_mass_fracs,
                                GLIR, oil_prod, water_prod, tp):
    """
    Generate initial gas stream for lifting

    :param gas: (Gas) the current Field's ``Gas`` instance
    :param imported_fuel_gas_comp: (float) Pandas Series imported fuel gas composition
    :param imported_fuel_gas_mass_fracs: (float) Pandas.Series imported fuel gas mass fractions
    :param GLIR: (float) gas lifting injection ratio
    :param oil_prod: (float) oil production volume rate
    :param water_prod: (float) water production volume rate
    :param tp: (TemperaturePressure) object holding T and P for the stream returned
    :return: (Stream) initial gas lifting stream
    """
    series = (imported_fuel_gas_mass_fracs * GLIR * (oil_prod + water_prod) *
              gas.component_gas_rho_STP[imported_fuel_gas_comp.index])

    stream = Stream("gas lifting stream", tp)
    stream.set_rates_from_series(series, PHASE_GAS)
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
