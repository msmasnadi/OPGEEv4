import networkx as nx
from .container import Container
from .core import elt_name, instantiate_subelts, dict_from_list
from .error import OpgeeException, OpgeeIterationStop
from .log import getLogger
from .processes.thermodynamics import Oil
from .process import Process, Environment, Reservoir, Aggregator
from .stream import Stream
from .utils import getBooleanXML, flatten

_logger = getLogger(__name__)

class Field(Container):
    """
    A `Field` contains all the `Process` instances associated with a single oil or
    gas field, and the `Stream` instances that connect them. It also holds instances
    of `Reservoir` and `Environment`, which are sources and sinks, respectively, in
    the process structure.
    """

    # TBD: can a field have any Processes that are not within Aggregator nodes?
    def __init__(self, name, attr_dict=None, aggs=None, procs=None, streams=None):

        # Note that `procs` are just those Processes defined at the top-level of the field
        super().__init__(name, attr_dict=attr_dict, aggs=aggs, procs=procs)

        self.stream_dict  = dict_from_list(streams)

        all_procs = self.collect_processes()
        self.process_dict = dict_from_list(all_procs)

        self.environment = Environment()    # TBD: is Environment per Field or per Analysis?
        self.reservoir   = Reservoir(name)  # TBD: One per field?
        self.extend = False

        # we use networkx to reason about the directed graph of Processes (nodes)
        # and Streams (edges).
        self.graph = g = self._connect_processes()

        self.cycles = list(nx.simple_cycles(g))
        self.run_order = None if self.cycles else nx.topological_sort(g)

        if self.cycles:
            _logger.info(f"Field '{name}' has cycles")

        gas_comp = self.attrs_with_prefix('gas_comp_')
        API = self.attr("API")
        gas_oil_ratio = self.attr('GOR')
        self.oil = Oil(API, gas_comp, gas_oil_ratio)

    def __str__(self):
        return f"<Field '{self.name}'>"

    def run(self, **kwargs):
        """
        Run all Processes defined for this Field, in the order computed from the graph
        characteristics. Container if `names` is None, otherwise run only the
        children whose names are in in `names`.

        :param names: (None, or list of str) the names of children to run
        :param kwargs: (dict) arbitrary keyword args to pass through
        :return: None
        """

        # TBD: this doesn't work when the upstream processes include a cycle
        def _impute_upstream(proc):
            # recurse upstream, calling impute()
            if proc:
                proc.impute()
                for s in proc.inputs:
                    _impute_upstream(s.src_proc)

        if self.is_enabled():
            self.iteration_reset()

            _logger.debug(f"Running '{self}'")

            start_streams = self.find_start_streams()
            for s in start_streams:
                _logger.info(f"Running impute() methods for procs upstream of start stream {s}")

                src_proc = s.src_proc
                if src_proc:
                    if self.is_cycle_member(src_proc):
                        raise OpgeeException(f"Can't run impute(): process {src_proc} is part of a process cycle")
                    _impute_upstream(src_proc)

            if not self.cycles:
                for proc in self.run_order:
                    proc.run_or_bypass(**kwargs)
            else:
                self.iterate_processes(**kwargs)

    def is_cycle_member(self, process):
        """
        Return True if `process` is a member of any process cycle.

        :param process: (Process)
        :return: (bool)
        """
        return any([process in cycle for cycle in self.cycles])

    # TBD: move these static methods to graph.py
    def ancestors(self, process):
        """
        Return a Process's immediate ancestor Processes.

        :param process: (Process) the starting Process
        :return: (list of Process) the Processes that are the sources of
           Streams connected to `process`.
        """
        procs = [stream.src_proc for stream in process.inputs]
        return procs

    def depends_on_cycle(self, process, visited=None):
        visited = visited or set()

        for ancestor in self.ancestors(process):
            if ancestor in visited:
                return True

            visited.add(ancestor)
            if self.depends_on_cycle(ancestor, visited=visited):
                return True

        return False

    def compute_graph_sections(self):
        """
        Divide the nodes of ``self.graph`` into three disjoint sets:
        1. Nodes neither in cycle nor dependent on cycles
        2. Nodes in cycles
        3. Nodes dependent on cycles

        :return: (3-tuple of lists of Processes)
        """
        processes = self.processes()
        cycles = self.cycles
        procs_in_cycles = set(flatten(cycles)) if cycles else []

        # reset visited flags since we use these to avoid cycling
        # self.iteration_reset()

        cycle_dependent = set()
        for process in processes:
            if process not in procs_in_cycles and self.depends_on_cycle(process):
                cycle_dependent.add(process)

        cycle_independent = set(processes) - procs_in_cycles - cycle_dependent
        return (cycle_independent, procs_in_cycles, cycle_dependent)


    def iterate_processes(self, **kwargs):
        cycle_independent, procs_in_cycles, cycle_dependent = self.compute_graph_sections()

        def run_procs_in_order(processes):
            sg = self.graph.subgraph(processes)
            run_order = nx.topological_sort(sg)
            for proc in run_order:
                proc.run_or_bypass(**kwargs)

        # run all the cycle-independent nodes in topological order
        run_procs_in_order(cycle_independent)

        # Iterate on the processes in cycle until a termination condition is met and an
        # OpgeeIterationStop exception is thrown.
        while True:
            try:
                for proc in procs_in_cycles:
                    proc.run_or_bypass(**kwargs)

            except OpgeeIterationStop as e:
                _logger.info(e)
                break

        # run all processes dependent on cycles, which are now complete
        run_procs_in_order(cycle_dependent)

    def _connect_processes(self):
        """
        Connect streams and processes in a directed graph.

        :return: (networkx.DiGraph) a directed graph representing the processes and streams.
        """
        # g = nx.DiGraph()
        g = nx.MultiDiGraph()  # allows parallel edges

        # first add all defined Processes since some (Exploration, Development & Drilling)
        # have no streams associated with them, but we still need to run the processes.
        for p in self.processes():
            g.add_node(p)

        for s in self.streams():
            s.src_proc = src = self.find_process(s.src_name)
            s.dst_proc = dst = self.find_process(s.dst_name)

            src.add_output_stream(s)
            dst.add_input_stream(s)

            g.add_edge(src, dst, stream=s)

        return g

    def streams(self):
        """
        Gets all `Stream` instances for this `Field`.

        :return: (iterator of `Stream` instances) streams in this `Field`
        """
        return self.stream_dict.values()

    def processes(self):
        """
        Gets all instances of subclasses of `Process` for this `Field`.

        :return: (iterator of `Process` (subclasses) instances) in this `Field`
        """
        return self.process_dict.values()

    def iteration_reset(self):
        for proc in self.processes():
            proc.iteration_reset()

    def find_stream(self, name, raiseError=True):
        """
        Find the Stream with `name` in this Field. If not found: if
        `raiseError` is True, an error is raised, else None is returned.

        :param name: (str) the name of the Stream to find
        :param raiseError: (bool) whether to raise an error if the Stream is not found.
        :return: (Stream or None) the requested Stream, or None if not found and `raiseError` is False.
        :raises: OpgeeException if `name` is not found and `raiseError` is True
        """
        stream = self.stream_dict.get(name)

        if stream is None and raiseError:
            raise OpgeeException(f"Stream named '{name}' was not found in field '{self.name}'")

        return stream

    def find_process(self, name, raiseError=True):
        """
        Find the Process of class `name` in this Field. If not found: if
        `raiseError` is True, an error is raised, else None is returned.

        :param name: (str) the name of the subclass of Process to find
        :param raiseError: (bool) whether to raise an error if the Process is not found.
        :return: (Process or None) the requested Process, or None if not found and `raiseError` is False.
        :raises: OpgeeException if `name` is not found and `raiseError` is True
        """
        process = self.process_dict.get(name)

        if process is None and raiseError:
            raise OpgeeException(f"Process named '{name}' was not found in field '{self.name}'")

        return process

    def find_start_streams(self):
        streams = [s for s in self.streams() if s.has_exogenous_data]
        return streams

    def set_extend(self, extend):
        self.extend = extend

    def report(self):
        print(f"\n*** Streams for field {self.name}")
        for stream in self.streams():
            print(f"{stream}\n{stream.components}\n")

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Field> element
        :return: (Field) instance populated from XML
        """
        name = elt_name(elt)

        # TBD: fill in Smart Defaults here, or assume they've been filled already?
        attr_dict = cls.instantiate_attrs(elt)

        aggs    = instantiate_subelts(elt, Aggregator)
        procs   = instantiate_subelts(elt, Process)
        streams = instantiate_subelts(elt, Stream)

        obj = Field(name, attr_dict=attr_dict, aggs=aggs, procs=procs, streams=streams)

        attrib = elt.attrib
        obj.set_enabled(getBooleanXML(attrib.get('enabled', '1')))
        obj.set_extend(getBooleanXML(attrib.get('extend', '0')))

        return obj

    def collect_processes(self):
        """
        Recursively descend the Field's Aggregators to create a list of all
        processes defined for this field.

        :return: (list of instances of Process subclasses) the processes
           defined for this field
        """
        def _collect(process_list, obj):
            for child in obj.children():
                if isinstance(child, Process):
                    process_list.append(child)
                else:
                    _collect(process_list, child)

        processes = []
        _collect(processes, self)
        return processes
