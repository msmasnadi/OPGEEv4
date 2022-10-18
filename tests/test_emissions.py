import pytest
import pandas as pd
from opgee import ureg
from opgee.emissions import Emissions, EM_FUGITIVES, EM_FLARING, EM_LAND_USE, EmissionsError
from opgee.error import OpgeeException


def test_set_rate():
    e = Emissions()
    rate = ureg.Quantity(123.45, 'tonne/day')
    e.set_rate(EM_FUGITIVES, 'CO2', rate)
    assert e.data.loc['CO2', EM_FUGITIVES] == rate


def test_set_rate_error():
    """Test that an unknown gas name throws an EmissionsError"""
    e = Emissions()

    with pytest.raises(EmissionsError, match=r".*Unrecognized gas*"):
        e.set_rate(EM_FUGITIVES, 'H2O', 43)


@pytest.fixture
def emissions_of_two_gases():
    e = Emissions()
    e.set_rates(EM_LAND_USE, CO2=123.45, N2O=45.6)
    return e.data


@pytest.mark.parametrize(
    "gas,rate", [('CO2', 123.45), ('N2O', 45.6), ('CO', 0.0), ('CH4', 0.0), ('VOC', 0.0)]
)
def test_set_rates(emissions_of_two_gases, gas, rate):
    assert emissions_of_two_gases.loc[gas, EM_LAND_USE] == ureg.Quantity(rate, 'tonne/day')


def test_set_rates_error1():
    """Test that an unknown gas name (as keyword arg) throws an EmissionsError"""
    e = Emissions()

    with pytest.raises(EmissionsError, match=r".*Unrecognized gas*"):
        e.set_rates(EM_FLARING, H2O=123.45)


def test_set_rates_error2():
    """Test that an unknown category name throws an EmissionsError"""
    e = Emissions()

    with pytest.raises(EmissionsError, match=r".*Unrecognized category*"):
        e.set_rates('Not-a-category', CO2=123.45)


@pytest.fixture
def emissions_for_gwp():
    e = Emissions()
    e.set_rates(EM_FLARING, CO2=1000, N2O=10, CH4=2, CO=1, VOC=1)
    return e


@pytest.mark.parametrize(
    "gwp_horizon, gwp_version, expected",
    [(20, 'AR4', 1000 + 10 * 289 + 2 * 72 + 7.65 + 14),
     (20, 'AR5', 1000 + 10 * 264 + 2 * 84 + 7.65 + 14),
     (20, 'AR5_CCF', 1000 + 10 * 298 + 2 * 86 + 18.6 + 14),
     (100, 'AR4', 1000 + 10 * 298 + 2 * 25 + 1.6 + 3.1),
     (100, 'AR5', 1000 + 10 * 265 + 2 * 28 + 2.7 + 4.5),
     ]
)
def test_gwp(test_model, emissions_for_gwp, gwp_horizon, gwp_version, expected):
    original_rates = emissions_for_gwp.data.copy()
    analysis = test_model.get_analysis('test')
    analysis.use_GWP(gwp_horizon, gwp_version)

    rates = emissions_for_gwp.rates(gwp=analysis.gwp)

    # check that original rates are unchanged
    assert all(rates == original_rates)

    # print(f"GHG for ({gwp_horizon}, {gwp_version} => {ghg}")
    assert rates.loc['GHG', EM_FLARING] == ureg.Quantity(pytest.approx(expected), 'tonne/day')


def test_use_GWP_error(test_model):
    with pytest.raises(OpgeeException, match=r".*GWP version must be one of*"):
        analysis = test_model.get_analysis('test')
        analysis.use_GWP(20, 'AR4_CCF')


def test_units():
    Emissions._units == ureg.Unit("tonne/day")


def test_add_from_series():
    em = Emissions()
    d = {'CO': 1.0, 'C1': 2.0, 'CO2': 3.0}
    s = pd.Series(d, dtype="pint[tonne/day]")
    em.add_from_series(EM_FLARING, s)
    for series_name, em_name in (('CO', 'CO'), ('C1', 'CH4'), ('CO2', 'CO2')):
        assert em.data.loc[em_name, EM_FLARING] == ureg.Quantity(d[series_name], 'tonne/day')
