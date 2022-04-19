from opgee import ureg
from opgee.stream import Stream
from opgee.process import Process
from .utils_for_tests import load_test_model

class LoopProc1(Process):
    def run(self, analysis):
        # find appropriate streams by checking connected processes' capabilities
        oil_flow_rate = ureg.Quantity(100.0, Stream.units())

        out_stream = self.find_output_stream('crude oil')
        out_stream.set_liquid_flow_rate('oil', oil_flow_rate)


class LoopProc2(Process):
    def run(self, analysis):
        h2_stream  = self.find_input_stream('hydrogen')
        h2_rate = h2_stream.gas_flow_rate('H2')

        ng_stream = self.find_output_stream('natural gas')
        ng_rate = h2_rate * 2
        ng_stream.set_gas_flow_rate('C1', ng_rate)

        # use this variable to detect process loop stabilization
        self.set_iteration_value(ng_rate)


class LoopProc3(Process):
    def run(self, analysis):
        ng_stream = self.find_input_stream('natural gas')
        ng_rate = ng_stream.gas_flow_rate('C1')

        h2_stream  = self.find_output_stream('hydrogen')
        co2_stream = self.find_output_stream('CO2')

        h2_rate  = ng_rate * 0.5
        co2_rate = ng_rate * 1.5

        h2_stream.set_gas_flow_rate('H2', h2_rate)
        co2_stream.set_gas_flow_rate('CO2', co2_rate)

        self.set_iteration_value((h2_rate, co2_rate)) # test multiple values


class LoopProc4(Process):
    def run(self, analysis):
        from opgee.emissions import EM_FLARING
        co2_stream = self.find_input_stream('CO2')
        co2_rate = co2_stream.gas_flow_rate('CO2')

        self.add_emission_rate(EM_FLARING, 'CO2', co2_rate)

def test_process_loop():
    m = load_test_model('test_process_loop_model.xml')
    analysis = m.get_analysis('test')

    field = analysis.get_field('test_single_loop')
    field.run(analysis, compute_ci=False)

    # TODO: this fails owing to an impute loop
    # field = analysis.get_field('test_double_loops')
    # field.run(analysis, compute_ci=False)
