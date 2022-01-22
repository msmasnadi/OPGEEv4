import pytest
from opgee.error import OpgeeException
from opgee.process import Process

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

    with pytest.raises(OpgeeException, match=".*streams are all empty"):
        proc3.find_output_streams('hydrogen', combine=True)

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

