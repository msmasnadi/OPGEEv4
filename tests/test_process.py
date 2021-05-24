import pytest
from opgee import ureg
from opgee.error import OpgeeException
from opgee.process import Process, _get_subclass

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

    rate_co2 = ureg.Quantity(100, 'tonne/day')
    rate_ch4 = ureg.Quantity( 30, 'tonne/day')
    rate_n2o = ureg.Quantity(  6, 'tonne/day')

    procA.add_emission_rates(CO2=rate_co2, CH4=rate_ch4, N2O=rate_n2o)
    (rates, co2eq) = procA.get_emission_rates(analysis)

    assert (rates.N2O == rate_n2o and rates.CH4 == rate_ch4 and rates.CO2 == rate_co2)

# TBD test these:
# process.get_environment
# process.get_reservoir
# find_input_streams failure to find a stream_type
