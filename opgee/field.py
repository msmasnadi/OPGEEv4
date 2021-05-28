import networkx as nx
from .container import Container
from .core import elt_name, instantiate_subelts, dict_from_list
from .error import OpgeeException, OpgeeStopIteration
from .log import getLogger
from .process import Process, Environment, Reservoir, Aggregator
from .stream import Stream
from .thermodynamics import Oil, Gas
from .utils import getBooleanXML, flatten

_logger = getLogger(__name__)


class Field(Container):
    """
    A `Field` contains all the `Process` instances associated with a single oil or
    gas field, and the `Stream` instances that connect them. It also holds instances
    of `Reservoir` and `Environment`, which are sources and sinks, respectively, in
    the process structure.
    """
    def __init__(self, name, attr_dict=None, aggs=None, procs=None, streams=None, group_names=None):
        # Note that `procs` include only Processes defined at the top-level of the field.
        # Other Processes maybe defined within the Aggregators in `aggs`.
        super().__init__(name, attr_dict=attr_dict, aggs=aggs, procs=procs)

        self._model = None  # set in _after_init

        self.group_names = group_names
        self.stream_dict = dict_from_list(streams)

        self.environment = Environment()    # one per field
        self.reservoir   = Reservoir(name)  # one per field

        all_procs = self.collect_processes() # includes reservoir and environment
        self.process_dict = self.adopt(all_procs, asDict=True)

        self.extend = False

        # we use networkx to reason about the directed graph of Processes (nodes)
        # and Streams (edges).
        self.graph = g = self._connect_processes()

        self.cycles = cycles = list(nx.simple_cycles(g))
        self.run_order = None if self.cycles else nx.topological_sort(g)

        if cycles:
            _logger.info(f"Field '{name}' has cycles: {cycles}")

        self.oil = Oil(self)
        self.gas = Gas(self)

    def _after_init(self):
        self.model = self.find_parent('Model')

    def __str__(self):
        return f"<Field '{self.name}'>"

    def _impute(self):
        max_iter = self.model.maximum_iterations

        # recursive helper function
        def _impute_upstream(proc):
            # recurse upstream, calling impute()
            if proc:
                if proc.visit() >= max_iter:
                    raise OpgeeStopIteration(f"Maximum iterations ({max_iter}) reached in {self}")

                proc.impute()

                upstream_procs = {stream.src_proc for stream in proc.inputs if stream.impute}
                for upstream_proc in upstream_procs:
                    _impute_upstream(upstream_proc)

        start_streams = self.find_start_streams()

        for stream in start_streams:
            if not stream.impute:
                raise OpgeeException(f"A start stream {stream} cannot have its 'impute' flag set to '0'.")

        # Find procs with start == True or find start_procs upstream from streams with exogenous data.from
        # We require that all start streams emerge from one Process.
        start_procs = {p for p in self.processes() if p.start} or {stream.src_proc for stream in start_streams}

        if len(start_procs) != 1:
            raise OpgeeException(f"Expected one start process upstream from start streams, got {len(start_procs)}: {start_procs}")

        start_proc = start_procs.pop()
        _logger.info(f"Running impute() methods for {start_proc}")

        try:
            _impute_upstream(start_proc)
        except OpgeeStopIteration as e:
            raise OpgeeException("Impute failed due to a process loop. Use Stream attribute impute='0' to break cycle.")

    def run(self, analysis):
        """
        Run all Processes defined for this Field, in the order computed from the graph
        characteristics, using the settings in `analysis` (e.g., GWP).

        :param analysis: (Analysis) the `Analysis` to use for analysis-specific settings.
        :return: None
        """
        if self.is_enabled():
            _logger.debug(f"Running '{self}'")

            self.iteration_reset()
            self._impute()

            self.iteration_reset()
            self.run_processes(analysis)

    def _is_cycle_member(self, process):
        """
        Return True if `process` is a member of any process cycle.

        :param process: (Process)
        :return: (bool)
        """
        return any([process in cycle for cycle in self.cycles])

    def _depends_on_cycle(self, process, visited=None):
        visited = visited or set()

        for predecessor in process.predecessors():
            if predecessor in visited:
                return True

            visited.add(predecessor)
            if self._depends_on_cycle(predecessor, visited=visited):
                return True

        return False

    def _compute_graph_sections(self):
        """
        Divide the nodes of ``self.graph`` into three disjoint sets:
        1. Nodes neither in cycle nor dependent on cycles
        2. Nodes in cycles
        3. Nodes dependent on cycles

        :return: (3-tuple of lists of Processes)
        """
        processes = self.processes()
        cycles = self.cycles

        procs_in_cycles = set(flatten(cycles)) if cycles else set()
        cycle_dependent = set()

        if cycles:
            for process in processes:
                if process not in procs_in_cycles and self._depends_on_cycle(process):
                    cycle_dependent.add(process)

        cycle_independent = set(processes) - procs_in_cycles - cycle_dependent
        return cycle_independent, procs_in_cycles, cycle_dependent

    def run_processes(self, analysis):
        cycle_independent, procs_in_cycles, cycle_dependent = self._compute_graph_sections()

        # helper function
        def run_procs_in_order(processes):
            if not processes:
                return

            sg = self.graph.subgraph(processes)
            run_order = nx.topological_sort(sg)
            for proc in run_order:
                proc.run_or_bypass(analysis)

        # run all the cycle-independent nodes in topological order
        run_procs_in_order(cycle_independent)

        # Iterate on the processes in cycle until a termination condition is met and an
        # OpgeeStopIteration exception is thrown.
        if procs_in_cycles:
            while True:
                try:
                    for proc in procs_in_cycles:
                        proc.run_or_bypass(analysis)

                except OpgeeStopIteration as e:
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

    def report(self, analysis):
        print(f"\n*** Streams for field {self.name}")
        for stream in self.streams():
            print(f"{stream}\n{stream.components}\n")

        self.report_energy_and_emissions(analysis)

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
        group_names = [node.text for node in elt.findall('Group')]

        obj = Field(name, attr_dict=attr_dict, aggs=aggs, procs=procs,
                    streams=streams, group_names=group_names)

        attrib = elt.attrib
        obj.set_enabled(getBooleanXML(attrib.get('enabled', '1')))
        obj.set_extend(getBooleanXML(attrib.get('extend', '0')))

        return obj

    def collect_processes(self):
        """
        Recursively descend the Field's Aggregators to create a list of all
        processes defined for this field. Includes Field's environment and reservoir
        automatically.

        :return: (list of instances of Process subclasses) the processes
           defined for this field
        """
        def _collect(process_list, obj):
            for child in obj.children():
                if isinstance(child, Process):
                    process_list.append(child)
                else:
                    _collect(process_list, child)

        processes = [self.environment, self.reservoir]
        _collect(processes, self)
        return processes
