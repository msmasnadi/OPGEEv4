import pytest
from opgee import ureg
from opgee.energy import EN_NATURAL_GAS, EN_CRUDE_OIL
from opgee.error import OpgeeException
from opgee.process import Process, _get_subclass, Environment, Reservoir

class NotProcess(): pass

def test_subclass_lookup_good(test_model):
    assert _get_subclass(Process, 'ProcA')

def test_subclass_lookup_bad_subclass(test_model):
    with pytest.raises(OpgeeException, match=r'Class .* is not a known subclass of .*'):
        _get_subclass(Process, 'NonExistentProcess')

def test_subclass_lookup_bad_parent(test_model):
    with pytest.raises(OpgeeException, match=r'lookup_subclass: cls .* must be one of .*'):
        _get_subclass(NotProcess, 'NonExistentProcess')

def test_set_emission_rates(test_model):
    analysis = test_model.get_analysis('test')
    field = analysis.get_field('test')
    procA = field.find_process('ProcA')

    rate_co2 = ureg.Quantity(100.0, 'tonne/day')
    rate_ch4 = ureg.Quantity( 30.0, 'tonne/day')
    rate_n2o = ureg.Quantity(  6.0, 'tonne/day')

    procA.add_emission_rates(CO2=rate_co2, CH4=rate_ch4, N2O=rate_n2o)
    (rates, co2eq) = procA.get_emission_rates(analysis)

    assert (rates.N2O == rate_n2o and rates.CH4 == rate_ch4 and rates.CO2 == rate_co2)

def test_add_energy_rates(test_model):
    analysis = test_model.get_analysis('test')
    field = analysis.get_field('test')
    procA = field.find_process('ProcA')

    unit = ureg.Unit('mmbtu/day')
    ng_rate = ureg.Quantity(123.45, unit)
    oil_rate = ureg.Quantity(4321.0, unit)

    procA.add_energy_rates({EN_NATURAL_GAS: ng_rate, EN_CRUDE_OIL: oil_rate})

    rates = procA.get_energy_rates(analysis)

    assert (rates[EN_NATURAL_GAS] == ng_rate and rates[EN_CRUDE_OIL] == oil_rate)

@pytest.fixture(scope='module')
def process(test_model):
    analysis = test_model.get_analysis('test')
    field = analysis.get_field('test')
    proc = field.find_process('ProcA')
    return proc

def test_get_environment(process):
    assert isinstance(process.get_environment(),  Environment)

def test_get_reservoir(process):
    assert isinstance(process.get_reservoir(),  Reservoir)

def test_find_input_streams_error(process):
    stream_type = 'unknown_stream_type'
    with pytest.raises(OpgeeException, match=f".* no input streams connect to processes handling '{stream_type}'"):
        process.find_input_streams(stream_type)

def test_venting_fugitive_rate_error(process):
    classname = process.__class__.__name__
    with pytest.raises(OpgeeException, match=f"'Class {classname}' was not found in table 'venting_fugitives_by_process'"):
        process.venting_fugitive_rate()

def test_venting_fugitive_rate(test_model):
    from opgee.processes import Drilling

    analysis = test_model.get_analysis('test')
    field = analysis.get_field('test')
    drilling = Drilling("OtherName")
    drilling.parent = field

    rate = drilling.venting_fugitive_rate()

    # mean of 1000 random draws from uniform(0.001, .003) should be ~0.002
    assert rate == pytest.approx(0.002, abs=0.0005)

