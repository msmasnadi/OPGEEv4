from opgee.units import ureg
from opgee.stream import Stream, PHASE_LIQUID
from opgee.process import Process
from .utils_for_tests import load_test_model


class LoopProc1(Process):
    def run(self, analysis):
        # find appropriate streams by checking connected processes' capabilities
        oil_flow_rate = ureg.Quantity(100.0, Stream.units())

        out_stream = self.find_output_stream('oil')
        out_stream.set_liquid_flow_rate('oil', oil_flow_rate)


class LoopProc2(Process):
    def run(self, analysis):
        crude_oil = self.find_input_stream('oil')
        recycled_water = self.find_input_stream("water")

        if crude_oil.is_uninitialized() and recycled_water.is_uninitialized():
            return

        output = self.find_output_stream("oil")
        output.copy_flow_rates_from(crude_oil)
        output.set_liquid_flow_rate("H2O", recycled_water.liquid_flow_rate("H2O"))
        self.set_iteration_value(output.total_flow_rate())


class LoopProc3(Process):
    def run(self, analysis):
        input = self.find_input_stream("oil")
        if input.is_uninitialized():
            return
        water = input.liquid_flow_rate("H2O")
        water_requirement = ureg.Quantity(160, "tonne/day")

        recycling_water = min(water * 0.8, water_requirement)
        recycle_stream = self.find_output_stream("water")
        recycle_stream.set_liquid_flow_rate("H2O", recycling_water)

        export = self.find_output_stream("export oil")
        export.copy_flow_rates_from(input)
        export.subtract_rates_from(recycle_stream, phase=PHASE_LIQUID)

        self.set_iteration_value(export.total_flow_rate())  # test multiple values


class LoopProc4(Process):
    def run(self, analysis):
        input = self.find_input_stream("export oil")
        if input.is_uninitialized():
            return
        gas = input.gas_flow_rate("C1")
        lifting_gas_requirement = ureg.Quantity(350, "tonne/day")

        lifting_gas = min(gas * 0.8, lifting_gas_requirement)
        lifting_gas_stream = self.find_output_stream("lifting gas")
        lifting_gas_stream.set_gas_flow_rate("C1", lifting_gas)

        export = self.find_output_stream("export oil")
        export.copy_flow_rates_from(input)
        export.subtract_rates_from(lifting_gas_stream)

        self.set_iteration_value(export.total_flow_rate())


def test_process_single_loop():
    process_loop_model = load_test_model('test_process_loop_model.xml')
    analysis = process_loop_model.get_analysis('test')
    field = analysis.get_field('test_single_loop')
    field.run(analysis, compute_ci=False)


def test_process_double_loops():
    process_loop_model = load_test_model('test_process_loop_model.xml')
    analysis = process_loop_model.get_analysis('test')
    field = analysis.get_field('test_double_loops')
    field.run(analysis, compute_ci=False)

# TBD: add tests that no elements of cycle are tagged run-after=True in XML
