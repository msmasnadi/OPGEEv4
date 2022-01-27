import pytest
from opgee import ureg
from opgee.energy import EN_NATURAL_GAS, EN_CRUDE_OIL
from opgee.emissions import EM_FLARING
from opgee.error import OpgeeException
from opgee.process import Process, _get_subclass, Environment, Reservoir
from opgee.stream import Stream

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
    rate_ch4 = ureg.Quantity(30.0, 'tonne/day')
    rate_n2o = ureg.Quantity(6.0, 'tonne/day')

    procA.add_emission_rates(EM_FLARING, CO2=rate_co2, CH4=rate_ch4, N2O=rate_n2o)
    df = procA.get_emission_rates(analysis)
    rates = df[EM_FLARING]

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
    assert isinstance(process.get_environment(), Environment)


def test_get_reservoir(process):
    assert isinstance(process.get_reservoir(), Reservoir)


@pytest.fixture(scope='module')
def procB(test_model):
    analysis = test_model.get_analysis('test')
    field = analysis.get_field('test')
    proc = field.find_process('ProcB')
    return proc


def test_find_input_streams_dict(procB):
    obj = procB.find_input_streams("crude oil")
    assert isinstance(obj, dict) and len(obj) == 1


def test_find_input_streams_list(procB):
    obj = procB.find_input_streams("crude oil", as_list=True)
    assert isinstance(obj, list) and len(obj) == 1


def test_find_input_stream(procB):
    procB.find_input_stream("crude oil")


def test_find_output_stream(process):
    process.find_output_stream("crude oil")


def test_find_input_stream_error(procB):
    stream_type = 'unknown_stream_type'
    with pytest.raises(OpgeeException, match=f".* no input streams contain '{stream_type}'"):
        procB.find_input_stream(stream_type)


def test_venting_fugitive_rate(test_model):
    analysis = test_model.get_analysis('test')
    field = analysis.get_field('test')
    procA = field.find_process('ProcA')
    rate = procA.venting_fugitive_rate()

    # mean of 1000 random draws from uniform(0.001, .003) should be ~0.002
    assert rate == pytest.approx(0.002, abs=0.0005)


def test_set_intermediate_value(procB):
    value = 123.456
    unit = 'degF'
    q = ureg.Quantity(value, unit)

    iv = procB.iv
    iv.store('temp', q)
    row = iv.get('temp')

    assert row['value'] == q.m and ureg.Unit(row['unit']) == q.u


def test_bad_intermediate_value(procB):
    iv = procB.iv
    with pytest.raises(OpgeeException, match=f"An intermediate value for '.*' was not found"):
        row = iv.get('non-existent')


foo = 1.0
bar = dict(x=1, y=2)
baz = "a string"


@pytest.mark.parametrize(
    "name, value", [('foo', foo), ('bar', bar), ('baz', baz)])
def test_process_data(procB, name, value):
    field = procB.field
    field.save_process_data(foo=foo, bar=bar, baz=baz)

    assert field.get_process_data(name) == value


def test_bad_process_data(procB):
    with pytest.raises(OpgeeException, match='Process data dictionary does not include .*'):
        procB.field.get_process_data("nonexistent-data-key", raiseError=True)


def test_combust_stream(procB):
    from opgee.core import TemperaturePressure
    stream = Stream("test_stream", TemperaturePressure(ureg.Quantity(100, "degF"),
                                                       ureg.Quantity(100, "psia")))
    stream.set_gas_flow_rate("C1", ureg.Quantity(10, "tonne/day"))
    stream.set_gas_flow_rate("C2", ureg.Quantity(20, "tonne/day"))
    stream.set_gas_flow_rate("N2", ureg.Quantity(15, "tonne/day"))

    result = procB.combust_stream(stream)
    assert result.gas_flow_rate("CO2") == ureg.Quantity(85.97773950086344, "tonne/day")
