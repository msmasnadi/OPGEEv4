import pytest

from opgee.energy import (
    EN_CRUDE_OIL,
    EN_DIESEL,
    EN_ELECTRICITY,
    EN_NATURAL_GAS,
    EN_PETCOKE,
    EN_RESID,
    Energy,
)
from opgee.error import OpgeeException
from opgee.units import ureg


def test_set_rate():
    e = Energy()
    rate = ureg.Quantity(123.45, 'mmbtu/day')
    e.set_rate(EN_DIESEL, rate)
    assert e.data[EN_DIESEL] == rate

def test_set_electricity():
    e = Energy()
    rate = ureg.Quantity(123.45, 'kWh/day')
    e.set_rate(EN_ELECTRICITY, rate)

    # Though set as "kWh/day", value is stored as "mmBtu/day", after conversion
    as_set = e.get_rate(EN_ELECTRICITY)
    assert as_set.u == Energy._units

    assert e.data[EN_ELECTRICITY] == rate

def test_set_rates_error():
    """Test that an unknown carrier name throws an OpgeeException"""
    e = Energy()

    with pytest.raises(OpgeeException, match=r".*Unrecognized carrier*"):
        e.set_rate('Uranium', 4321)

def test_add_rate():
    e = Energy()
    rate = ureg.Quantity(40.0, 'mmbtu/day')
    e.set_rate(EN_DIESEL, rate)
    e.add_rate(EN_DIESEL, rate)
    assert e.data[EN_DIESEL] == ureg.Quantity(80.0, 'mmbtu/day')

def test_add_rate_error():
    """Test that an unknown carrier name throws an OpgeeException"""
    e = Energy()

    with pytest.raises(OpgeeException, match=r".*Unrecognized carrier*"):
        e.add_rates({'Uranium': 4321})

@pytest.fixture
def two_carriers():
    e = Energy()
    e.set_rates({EN_NATURAL_GAS: 123.45, EN_DIESEL: 45.6})
    return e.data

@pytest.mark.parametrize(
    "carrier, rate", [(EN_NATURAL_GAS, 123.45), (EN_DIESEL, 45.6), (EN_CRUDE_OIL, 0.0),
                      (EN_PETCOKE, 0.0), (EN_RESID, 0.0)]
)
def test_set_rates(two_carriers, carrier, rate):
    assert two_carriers[carrier] == ureg.Quantity(rate, 'mmbtu/day')


def test_set_rates_error():
    """Test that an unknown gas name (as keyword arg) throws an OpgeeException"""
    e = Energy()

    with pytest.raises(OpgeeException, match=r".*Unrecognized carrier*"):
        e.set_rates({EN_NATURAL_GAS: 123.45, 'Random': 4321})
