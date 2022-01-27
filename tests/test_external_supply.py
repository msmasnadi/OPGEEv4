from opgee import ureg
from opgee.core import TemperaturePressure
from opgee.process import ExternalSupply
from opgee.stream import Stream

def test_external_supply():
    supply = ExternalSupply()

    stream = Stream("external supply", TemperaturePressure(ureg.Quantity(72.0, "degF"),
                                                           ureg.Quantity(100.0, "psia")))

    gas = ureg.Quantity(10, "tonne/day")
    supply.use_gas(stream, gas)

    water = ureg.Quantity(1000, "tonne/day")
    supply.use_water(stream, water)

    electricity = ureg.Quantity(150, "mmbtu/day")
    supply.use_electricity(electricity)

    assert supply.gas == gas
    assert supply.water == water
    assert supply.electricity == electricity

    supply.use_gas(stream, gas)
    supply.use_water(stream, 2 * water)
    supply.use_electricity(3 * electricity)

    assert supply.gas == 2 * gas
    assert supply.water == 3 * water
    assert supply.electricity == 4 * electricity

    supply.reset_totals()

    supply.use_gas(stream, gas)
    supply.use_water(stream, 2 * water)
    supply.use_electricity(3 * electricity)

    assert supply.gas == gas
    assert supply.water == 2 * water
    assert supply.electricity == 3 * electricity
