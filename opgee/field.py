import networkx as nx
from . import ureg
from .container import Container
from .core import elt_name, instantiate_subelts, dict_from_list
from .error import OpgeeException, OpgeeStopIteration, OpgeeMaxIterationsReached, OpgeeIterationConverged
from .log import getLogger
from .process import Process, Environment, Reservoir, Output, Aggregator, SurfaceSource
from .process_groups import ProcessChoice
from .stream import Stream
from .thermodynamics import Oil, Gas, Water
from .steam_generator import SteamGenerator
from .utils import getBooleanXML, flatten
from .energy import Energy

_logger = getLogger(__name__)


class Field(Container):
    """
    A `Field` contains all the `Process` instances associated with a single oil or
    gas field, and the `Stream` instances that connect them. It also holds instances
    of `Reservoir` and `Environment`, which are sources and sinks, respectively, in
    the process structure.
    """
    def __init__(self, name, attr_dict=None, aggs=None, procs=None, streams=None, group_names=None,
                 process_choice_dict=None):
        # Note that `procs` include only Processes defined at the top-level of the field.
        # Other Processes maybe defined within the Aggregators in `aggs`.
        super().__init__(name, attr_dict=attr_dict, aggs=aggs, procs=procs)

        self._model = None  # set in _after_init

        self.group_names = group_names
        self.stream_dict = dict_from_list(streams)

        self.process_choice_dict = process_choice_dict

        self.environment = Environment()    # one per field
        self.reservoir   = Reservoir()      # one per field
        self.surface_source = SurfaceSource() # one per field
        self.output = Output()

        self.carbon_intensity = ureg.Quantity(0.0, "g/MJ")

        all_procs = self.collect_processes() # includes reservoir and environment
        self.process_dict = self.adopt(all_procs, asDict=True)

        self.extend = False

        # we use networkx to reason about the directed graph of Processes (nodes)
        # and Streams (edges).
        self.graph = g = self._connect_processes()

        self.cycles = cycles = list(nx.simple_cycles(g))
        self.run_order = None if self.cycles else nx.topological_sort(g)

        if cycles:
            _logger.debug(f"Field '{name}' has cycles: {cycles}")

        self.oil = Oil(self)
        self.gas = Gas(self)
        self.water = Water(self)
        self.steam_generator = SteamGenerator(self)

        self.process_data = {}

    def _after_init(self):
        self.check_attr_constraints(self.attr_dict)

        self.model = self.find_parent('Model')

        for iterator in [self.processes(), self.streams(), [self.oil, self.gas, self.water, self.steam_generator]]:
            for obj in iterator:
                obj._after_init()

    def __str__(self):
        return f"<Field '{self.name}'>"

    def _impute(self):
        max_iter = self.model.maximum_iterations

        # recursive helper function
        def _impute_upstream(proc):
            # recurse upstream, calling impute()
            if proc and proc.enabled:
                if proc.visit() >= max_iter:
                    raise OpgeeMaxIterationsReached(f"Maximum iterations ({max_iter}) reached in {self}")

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
        start_procs = {p for p in self.processes() if p.impute_start} or {stream.src_proc for stream in start_streams}

        if len(start_procs) != 1:
            raise OpgeeException(f"Expected one start process upstream from start streams, got {len(start_procs)}: {start_procs}")

        start_proc = start_procs.pop()
        _logger.info(f"Running impute() methods for {start_proc}")

        try:
            _impute_upstream(start_proc)
        except OpgeeStopIteration:
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

            self.reset_streams()
            self.iteration_reset()
            self._impute()

            self.iteration_reset()
            self.run_processes(analysis)
            self.check_balances()

    def reset_streams(self):
        for stream in self.streams():
            # If a stream is disabled, leave it so. Otherwise disable it if either of
            # its source or destination processes is disabled.
            if stream.enabled and not (stream.src_proc.enabled and stream.dst_proc.enabled):
                stream.set_enabled(False)

            stream.reset()

    def check_balances(self):
        for p in self.processes():
            p.check_balances()

    def compute_carbon_intensity(self, analysis):
        rates = self.emissions.rates(analysis.gwp)
        emissions = rates.loc['GHG'].sum()
        energy = self.output.energy_flow

        ci = ureg.Quantity((emissions / energy) if energy else 0, 'grams/MJ')
        self.carbon_intensity = ci
        return ci

    def report(self, analysis):
        name = self.name

        print(f"\n*** Streams for field '{name}'")
        for stream in self.streams():
            print(f"{stream}\n{stream.components}\n")

        # Perform aggregations required by compute_carbon_intensity()
        self.report_energy_and_emissions(analysis)

        self.compute_carbon_intensity(analysis)

        print(f"Field '{name}': CI = {self.carbon_intensity:.2f}")

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

        :return: (3-tuple of sets of Processes)
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
                proc.run_if_enabled(analysis)

        # run all the cycle-independent nodes in topological order
        run_procs_in_order(cycle_independent)

        # If user has indicated a process with start-cycle="true", start there, otherwise
        # find a process with cycle-independent processes as inputs, and start there.
        start_procs = [proc for proc in procs_in_cycles if proc.cycle_start]
        if len(start_procs) > 1:
            raise OpgeeException(f"""Only one process per cycle can have cycle-start="true"; found {len(start_procs)}: {start_procs}""")

        if procs_in_cycles:
            # Walk the cycle, starting at the indicated start process to generate an ordered list
            unvisited = procs_in_cycles.copy()

            if start_procs:
                ordered_cycle = []

                # recursive function to walk successors until we've visited all the procs in the cycle
                def process_successors(proc):
                    if unvisited:
                        if proc in unvisited:
                            unvisited.remove(proc)
                            ordered_cycle.append(proc)

                            for successor in proc.successors():
                                process_successors(successor)

                process_successors(start_procs[0])
            else:
                # TBD: Compute ordering by looking for procs in cycle that are successors to cycle_independent procs.
                # TBD: For now, just copy run using procs_in_cycles.
                ordered_cycle = procs_in_cycles

            # Iterate on the processes in cycle until a termination condition is met and an
            # OpgeeStopIteration exception is thrown.
            while True:
                try:
                    for proc in ordered_cycle:
                        proc.run_if_enabled(analysis)

                except OpgeeIterationConverged as e:
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


    def process_choice_node(self, name, raiseError=True):
        """
        Find a `ProcessChoice` instance by name.

        :param name: (str) the name of the choice element
        :param raiseError: (bool) whether to raise an error if `name` is not found
        :return: (opgee.ProcessChoice) the instance found, or None
        """
        choice_node = self.process_choice_dict.get(name)
        if choice_node is None and raiseError:
            raise OpgeeException(f"Process choice '{name}' not found in field '{self.name}'")

        return choice_node

    def iteration_reset(self):
        for proc in self.processes():
            proc.reset_iteration()

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

        choices = instantiate_subelts(elt, ProcessChoice)
        # Convert to lowercase to avoid simple lookup errors
        process_choice_dict = {choice.name.lower() : choice for choice in choices}

        group_names = [node.text for node in elt.findall('Group')]

        obj = Field(name, attr_dict=attr_dict, aggs=aggs, procs=procs,
                    streams=streams, group_names=group_names,
                    process_choice_dict=process_choice_dict)

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

        processes = [self.environment, self.reservoir, self.surface_source, self.output]
        _collect(processes, self)
        return processes

    def save_process_data(self, **kwargs):
        """
        Allows a Process to store arbitrary data in the field's `process_data` dictionary
        for access by other processes.

        :param name: (str) the name of the data element (the dictionary key)
        :param value: (any) the value to store in the dictionary
        :return: none
        """
        for name, value in kwargs.items():
            self.process_data[name] = value

    def get_process_data(self, name, raiseError=None):
        """
        Retrieve a stored value from the field's `process_data` dictionary.

        :param name: (str) the name of the data element (the dictionary key)
        :return: (any) the value
        :raises OpgeeException: if the name is not found in `process_data`.
        """
        try:
            return self.process_data[name]
        except KeyError:
            if raiseError:
                raise OpgeeException(f"Process data dictionary does not include {name}")
            else:
                return None

    def resolve_process_choices(self):
        """
        Disable all processes referenced in a `ProcessChoice`, then enable only the processes
        in the selected `ProcessGroup`. The name of each `ProcessChoice` must also identify an
        field-level attribute, whose value indicates the user's choice of `ProcessGroup`.

        :return: None
        """
        attr_dict = self.attr_dict
        self.dump()
        #
        # Turn off all processes identified in groups, then turn on those in the selected groups.
        #
        for choice_name, choice in self.process_choice_dict.items():
            attr = attr_dict.get(choice_name)
            if attr is None:
                raise OpgeeException(f"ProcessChoice '{choice_name}' has no corresponding attribute in field '{self.name}'")

            to_enable = []
            selected_group_name = attr.value.lower()

            for group_name, group in choice.groups_dict.items():
                procs, streams = group.processes_and_streams(self)

                if group_name == selected_group_name:   # remember the ones to turn back on
                    to_enable.extend(procs)
                    to_enable.extend(streams)

                # disable all object in all groups
                for obj in procs + streams:
                    obj.set_enabled(False)

            # enable the chosen procs and streams
            for obj in to_enable:
                obj.set_enabled(True)

    def sum_process_energy(self, processes_to_exclude=None) -> Energy:

        total = Energy()
        processes_to_exclude = processes_to_exclude or []
        for proc in self.processes():
            if proc.enabled and proc.name not in processes_to_exclude:
                total.add_rates_from(proc.energy)

        return total

    def dump(self):
        """
        Print out a representation of the field's processes and streams for debugging.

        :return: none
        """
        import logging

        visited = {}    # traverse a process only the first time it's encountered

        def debug(msg):
            print(msg)

        def visit(process):
            visited[process] = True
            next = []

            debug(f"\n> {process} outputs:")
            for stream in process.outputs:
                debug(f"  * {stream}")
                dst = stream.dst_proc
                if not dst in visited:
                    next.append(dst)

            for proc in next:
                visit(proc)

        debug(f"\n{self}:")
        visit(self.reservoir)
