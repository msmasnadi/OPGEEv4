from opgee.emissions import Emissions
from opgee.error import OpgeeException
from opgee.model import Model
import pytest

@pytest.fixture
def gwp_100_AR4():
    analysis = None
    m = Model('test', analysis)
    m.use_GWP(100, 'AR4')
    return m.gwp

@pytest.fixture
def gwp_20_AR5():
    analysis = None
    m = Model('test', analysis)
    m.use_GWP(20, 'AR5')
    return m.gwp

@pytest.fixture
def gwp_20_AR5_CCF():
    analysis = None
    m = Model('test', analysis)
    m.use_GWP(20, 'AR5_CCF')
    return m.gwp


def test_set_rate():
    e = Emissions()
    e.set_rate('CO2', 123.45)
    assert e.data['CO2'] == 123.45

def test_set_rate_error():
    """Test that an unknown gas name throws an OpgeeException"""
    e = Emissions()

    with pytest.raises(OpgeeException, match=r".*Unrecognized gas*"):
        e.set_rate('H2O', 43)


@pytest.fixture
def emissions_of_two_gases():
    e = Emissions()
    e.set_rates(CO2=123.45, N2O=45.6)
    return e.data

@pytest.mark.parametrize(
    "gas,rate", [('CO2', 123.45), ('N2O', 45.6), ('CO', 0.0), ('CH4', 0.0), ('VOC', 0.0)]
)
def test_set_rates(emissions_of_two_gases, gas, rate):
    assert emissions_of_two_gases[gas] == rate


def test_set_rates_error():
    """Test that an unknown gas name (as keyword arg) throws an OpgeeException"""
    e = Emissions()

    with pytest.raises(OpgeeException, match=r".*Unrecognized gas*"):
        e.set_rates(H2O=123.45)

def test_gwp():
    e = Emissions()
    e.set_rates(CO2=100, N2O=10, CO=10, CH4=100, VOC=1)
