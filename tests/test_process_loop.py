import networkx as nx

from opgee import ureg
from opgee.stream import Stream
from opgee.process import Process, ProcessCycle
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
    process_loop_model = load_test_model('test_process_loop_model.xml')
    analysis = process_loop_model.get_analysis('test')
    field = analysis.get_field('test')
    field.run(analysis, compute_ci=False)


# TBD: add tests that no elements of cycle are tagged run-after=True in XML


def cycle_graph():
    """
    Generate a graph with nested cycles
    """
    g = nx.MultiDiGraph()
    nodes = ('A', 'B', 'C', 'D', 'E')
    edges = [
        ('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'E'),
        ('E', 'A'),  # outer cycle
        ('C', 'B'),  # inner cycle
        ('D', 'B')   # inner cycle
    ]

    for node in nodes:
        g.add_node(node)

    for src, dst in edges:
        g.add_edge(src, dst)

    return g

def test_nested_cycles():
    g = cycle_graph()

    # We'll only need to run the outer loops; they will contain all other processes
    outers = ProcessCycle.cycles(g)
    assert len(outers) == 1

    outer = outers[0]
    assert outer.node_set == set(['A', 'B', 'C', 'D', 'E'])

    assert len(outer.contains) == 1
    mid = outer.contains.pop()
    assert mid.node_set == set(['B', 'C', 'D'])

    assert len(mid.contains) == 1
    inner = mid.contains.pop()
    assert inner.node_set == set(['B', 'C'])
