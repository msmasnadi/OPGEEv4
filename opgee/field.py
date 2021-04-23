import networkx as nx

from .container import Container
from .core import A, elt_name, instantiate_subelts, dict_from_list
from .error import OpgeeException
from .log import getLogger
from .process import Process, Environment, Reservoir, Aggregator
from .stream import Stream
from .utils import getBooleanXML

_logger = getLogger(__name__)

class Field(Container):
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

        self.is_dag = nx.is_directed_acyclic_graph(g)
        self.run_order = nx.topological_sort(g) if self.is_dag else []
        if self.run_order is None:
            _logger.warn(f"Field '{name}' has cycles, which aren't supported yet")

    def __str__(self):
        return f"<Field name='{self.name}'>"

    def run(self, **kwargs):
        """
        Run all Processes defined for this Field, in the order computed from the graph
        characteristics. Container if `names` is None, otherwise run only the
        children whose names are in in `names`.

        :param names: (None, or list of str) the names of children to run
        :param kwargs: (dict) arbitrary keyword args to pass through
        :return: None
        """
        def _impute_upstream(proc):
            # recurse upstream, calling impute()
            if proc:
                proc.impute()
                for s in proc.inputs:
                    _impute_upstream(s.src_proc)

        if self.is_enabled():
            _logger.debug(f"Running '{self}'")

            start_streams = self.find_start_streams()
            for s in start_streams:
                _logger.info(f"Running impute() methods for procs upstream of start stream {s}")
                src_proc = s.src_proc
                if src_proc:
                    _impute_upstream(src_proc)

            for proc in self.run_order:
                proc.run(**kwargs)

    def _connect_processes(self):
        """
        Connect streams and processes to one another.

        :return: (networkx.DiGraph) a directed graph representing the processes and streams.
        """
        g = nx.DiGraph()

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

    def _clear_visited(self):
        for proc in self.processes():
            proc.clear_visit_count()

    def streams(self):
        return self.stream_dict.values()    # N.B. returns an iterator

    def processes(self):
        return self.process_dict.values()   # N.B. returns an iterator

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
        attr_dict = instantiate_subelts(elt, A, as_dict=True)

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

        :return: (list(Process)) the processes defined for this field
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
