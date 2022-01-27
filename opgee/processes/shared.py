from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL, EN_RESID
from ..error import OpgeeException
from ..stream import Stream, PHASE_GAS

# TODO: This didn't belong in the abstract Process class, so I moved it here
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
    air_cooler_energy_consumption = proc.get_energy_consumption("Electric_motor", blower_fan_motor_hp)
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

    raise OpgeeException(f"Unrecognized prime_move_type: '{prime_mover_type}'")
