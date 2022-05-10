import pytest
from opgee.error import OpgeeException
from opgee.process import Process
from opgee import ureg

from .utils_for_tests import load_test_model


class Proc1(Process):
    def run(self, analysis):
        pass


class Proc2(Process):
    def run(self, analysis):
        pass


class Proc3(Process):
    def run(self, analysis):
        pass


class Proc4(Process):
    def run(self, analysis):
        pass


@pytest.fixture(scope="module")
def stream_model(configure_logging_for_tests):
    return load_test_model('test_stream.xml')


def test_carbon_number():
    from opgee.stream import is_carbon_number
    assert is_carbon_number("C2") and is_carbon_number("C200")

    assert not is_carbon_number("foo")


def test_find_stream(stream_model):
    analysis = stream_model.get_analysis('test')
    field = analysis.get_field('test')

    name = 'stream1'
    s = field.find_stream(name)
    assert s.name == name

    bad_name = 'unknown_stream'
    with pytest.raises(OpgeeException, match=f"Stream named '{bad_name}' was not found .*"):
        field.find_stream(bad_name)

    proc3 = field.find_process('Proc3')

    stream = proc3.find_output_stream('CO2')
    assert stream and 'CO2' in stream.contents

    contents = 'hydrogen'
    with pytest.raises(OpgeeException, match=f"Expected one output stream with '{contents}'.*"):
        proc3.find_output_stream(contents)

    streams = proc3.find_output_streams('hydrogen', as_list=False)
    assert streams and type(streams) == dict and len(streams) == 2

    streams = proc3.find_output_streams('hydrogen', as_list=True)
    assert streams and type(streams) == list and len(streams) == 2

    with pytest.raises(OpgeeException, match=f".*both 'combine' and 'as_list' cannot be True"):
        proc3.find_output_streams('hydrogen', as_list=True, combine=True)

    streams = proc3.find_input_streams('natural gas', as_list=False)
    assert streams and type(streams) == dict

    streams = proc3.find_input_streams('natural gas', as_list=True)
    assert streams and type(streams) == list

    with pytest.raises(OpgeeException, match=f".*no input streams contain '{bad_name}'"):
        proc3.find_input_streams(bad_name, combine=False, as_list=False, raiseError=True)


def test_initialization(stream_model):
    analysis = stream_model.get_analysis('test')
    field = analysis.get_field('test')

    stream1 = field.find_stream('initialized')
    assert stream1.is_initialized() and not stream1.has_zero_flow()

    stream2 = field.find_stream("Proc3-to-Proc4")
    assert stream2.is_uninitialized() and stream2.has_zero_flow()

    stream2.set_gas_flow_rate("CO2", 0)
    assert stream2.is_initialized() and stream2.has_zero_flow()

    stream2.set_gas_flow_rate("CO2", 10)
    assert stream2.is_initialized() and not stream2.has_zero_flow()

    assert stream2.solid_flow_rate('PC').m == 0

    rates = stream1.non_zero_flow_rates()
    assert len(rates) == 1 and rates.index[0] == 'oil'
    oil = rates.loc['oil']
    assert oil.solid.m == 0.0 and oil.gas.m == 0.0 and oil.liquid.m == 100.0


def test_combustion_stream(stream_model):
    analysis = stream_model.get_analysis('test')
    field = analysis.get_field('test')
    stream1 = field.find_stream("combustion stream")
    CO2_stream = field.find_stream("combusted final stream")
    CO2_stream.add_combustion_CO2_from(stream1)
    assert CO2_stream.gas_flow_rate("CO2") == ureg.Quantity(pytest.approx(8.950127703143934), "t/d")

def test_stream_utils(stream_model):
    from opgee.core import TemperaturePressure
    from opgee.stream import Stream
    tp = None
    s = Stream('stream1', tp)
    assert s.tp == None

    tp = TemperaturePressure(100, 200)
    s.set_tp(tp)

    s.set_tp(None)  # TBD: silently does nothing. Probably should raise error instead

    # check that T & P are unchanged
    s.tp.T.m == 100.0
    s.tp.P.m == 200.0


def test_electricity(stream_model):
    from copy import copy

    analysis = stream_model.get_analysis('test')
    field = analysis.get_field('test')

    # copy so we don't alter model, in case we add more tests after this
    stream = copy(field.find_stream('initialized'))

    assert stream.electricity_flow_rate() == ureg.Quantity(0.0, "kWh/day")

    rate = ureg.Quantity(100.00, "kWh/day")
    stream.set_electricity_flow_rate(rate)
    assert stream.electricity_flow_rate() == rate

    factor = 3
    stream.multiply_flow_rates(factor)
    assert stream.electricity_flow_rate() == rate * factor

    stream2 = copy(stream)
    stream.add_flow_rates_from(stream2)
    assert stream.electricity_flow_rate() == rate * factor * 2

    stream2.copy_electricity_rate_from(stream)
    assert stream2.electricity_flow_rate() == stream.electricity_flow_rate()
