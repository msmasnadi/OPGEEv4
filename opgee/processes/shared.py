from ..energy import EN_NATURAL_GAS, EN_ELECTRICITY, EN_DIESEL
from ..error import OpgeeException
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

    air_cooler_delta_T           = _value(air_cooler_delta_T, proc.air_cooler_delta_T)
    water_press                  = _value(water_press, proc.water_press)
    air_cooler_fan_eff           = _value(air_cooler_fan_eff, proc.air_cooler_fan_eff)
    air_cooler_speed_reducer_eff = _value(air_cooler_speed_reducer_eff, proc.air_cooler_speed_reducer_eff)

    model = proc.field.model
    blower_air_quantity = thermal_load / model.const("air-elevation-corr") / air_cooler_delta_T
    blower_CFM = blower_air_quantity / model.const("air-density-ratio")
    blower_delivered_hp = blower_CFM * water_press / air_cooler_fan_eff
    blower_fan_motor_hp = blower_delivered_hp / air_cooler_speed_reducer_eff
    air_cooler_energy_consumption = proc.get_energy_consumption("Electric_motor", blower_fan_motor_hp)
    return air_cooler_energy_consumption.to("kWh/day")


def get_energy_carrier(prime_mover_type):
    if prime_mover_type.startswith("NG_"):
        return EN_NATURAL_GAS

    if prime_mover_type.startswith("Electric_"):
        return EN_ELECTRICITY

    if prime_mover_type.startswith("Diesel_"):
        return EN_DIESEL

    raise OpgeeException(f"Unrecognized prime_move_type: '{prime_mover_type}'")
