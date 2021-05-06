import pytest
from opgee.model import ModelFile
from opgee.process import Process
from opgee.stream import PHASE_GAS, PHASE_LIQUID

@pytest.fixture
def model(): # configure_logging_for_tests
    mf = ModelFile('files/test_model.xml', add_stream_components=False, use_class_path=False)
    return mf.model


class Proc1(Process):
    def run(self, **kwargs):
        # find appropriate streams by checking connected processes' capabilities
        oil_flow_rate = 100

        out_stream = self.find_output_stream('crude oil')
        out_stream.set_flow_rate('oil', PHASE_LIQUID, oil_flow_rate)


class Proc2(Process):
    def run(self, **kwargs):
        h2_stream  = self.find_input_streams('hydrogen')
        h2_rate = h2_stream.flow_rate('H2', PHASE_GAS)

        ng_stream = self.find_output_stream('natural gas')
        ng_rate = h2_rate * 2
        ng_stream.set_flow_rate('C1', PHASE_GAS, ng_rate)

        # use this variable to detect process loop stabilization
        self.set_iteration_value(ng_rate)


class Proc3(Process):
    def run(self, **kwargs):
        ng_stream = self.find_input_streams('natural gas')
        ng_rate = ng_stream.flow_rate('C1', PHASE_GAS)

        h2_stream  = self.find_output_stream('hydrogen')
        co2_stream = self.find_output_stream('CO2')

        h2_rate  = ng_rate * 0.5
        co2_rate = ng_rate * 1.5

        h2_stream.set_flow_rate('H2', PHASE_GAS, h2_rate)
        co2_stream.set_flow_rate('CO2', PHASE_GAS, co2_rate)


class Proc4(Process):
    def run(self, **kwargs):
        co2_stream = self.find_input_streams('CO2')
        co2_rate = co2_stream.flow_rate('CO2', PHASE_GAS)

        self.add_emission_rate('CO2', co2_rate)

def test_process_loop(model):
    model.validate()
    field = model.analysis.get_field('test')
    field.run()
    assert 1 == 1
