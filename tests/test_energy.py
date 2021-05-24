from opgee import ureg
from opgee.energy import Energy, EN_DIESEL, EN_NATURAL_GAS, EN_RESID, EN_PETCOKE, EN_CRUDE_OIL
from opgee.error import OpgeeException
import pytest

def test_set_rate():
    e = Energy()
    rate = ureg.Quantity(123.45, 'mmbtu/day')
    e.set_rate(EN_DIESEL, rate)
    assert e.data[EN_DIESEL] == rate

def test_set_rate_error():
    """Test that an unknown carrier name throws an OpgeeException"""
    e = Energy()

    with pytest.raises(OpgeeException, match=r".*Unrecognized carrier*"):
        e.set_rate('Uranium', 4321)


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
