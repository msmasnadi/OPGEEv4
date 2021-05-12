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


@pytest.fixture
def emissions_for_gwp():
    e = Emissions()
    e.set_rates(CO2=1000, N2O=10, CH4=2, CO=1, VOC=1)
    return e

@pytest.mark.parametrize(
    "gwp_horizon, gwp_version, expected",
    [(20,  'AR4',     1000 + 10 * 289 + 2 * 72 + 7.65 + 14),
     (20,  'AR5',     1000 + 10 * 264 + 2 * 84 + 7.65 + 14),
     (20,  'AR5_CCF', 1000 + 10 * 264 + 2 * 86 + 18.6 + 14),
     (100, 'AR4',     1000 + 10 * 298 + 2 * 25 +  1.6 + 3.1),
     (100, 'AR5',     1000 + 10 * 265 + 2 * 30 +  2.7 + 4.5),
     ]
)
def test_gwp(model, emissions_for_gwp, gwp_horizon, gwp_version, expected):
    original_rates = emissions_for_gwp.data.copy()
    analysis = model.get_analysis('test')
    analysis.use_GWP(gwp_horizon, gwp_version)

    rates, ghg = emissions_for_gwp.rates(gwp=analysis.gwp)

    # check that rates are unchanged
    assert all(rates == original_rates)

    #print(f"GHG for ({gwp_horizon}, {gwp_version} => {ghg}")
    assert ghg == pytest.approx(expected)

def test_use_GWP_error(model):
    with pytest.raises(OpgeeException, match=r".*GWP version must be one of*"):
        analysis = model.get_analysis('test')
        analysis.use_GWP(20, 'AR4_CCF')

