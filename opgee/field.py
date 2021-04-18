from .core import Container, A, elt_name, instantiate_subelts, dict_from_list
from .error import OpgeeException
from .process import Process, Environment, Reservoir, Aggregator
from .stream import Stream
from .utils import getBooleanXML

class Field(Container):
    # TBD: can a field have any Processes that are not within Aggregator nodes?
    def __init__(self, name, attrs=None, aggs=None, procs=None, streams=None):

        # Note that `procs` are just those Processes defined at the top-level of the field
        super().__init__(name, attrs=attrs, aggs=aggs, procs=procs)

        self.stream_dict  = dict_from_list(streams)

        all_procs = self.collect_processes()
        self.process_dict = process_dict = dict_from_list(all_procs)

        self.environment = Environment()    # TBD: is Environment per Field or per Analysis?
        self.reservoir   = Reservoir(name)  # TBD: One per field?
        self.extend = False

        self._connect_processes()

    def _connect_processes(self):
        """
        Connect streams and processes to one another.

        :return: none
        """
        for stream in self.streams():
            stream.src_proc = self.find_process(stream.src_name)
            stream.dst_proc = self.find_process(stream.dst_name)

            stream.src_proc.add_output_stream(stream)
            stream.dst_proc.add_input_stream(stream)

    def streams(self):
        return self.stream_dict.values()    # N.B. returns an iterator

    def processes(self):
        return self.process_dict.values()   # N.B. returns an iterator

    def find_stream(self, name, raiseError=True):
        """
        Find the Stream with `name` in this Field. If not found: if
        `raiseError` is True, an error is raised, else None is returned.

        :param name: (str) the name of the Stream to find
        :param raiseError: (bool) whether to raise an error if the Steam is not found.
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
        attrs = instantiate_subelts(elt, A)

        aggs    = instantiate_subelts(elt, Aggregator)
        procs   = instantiate_subelts(elt, Process)
        streams = instantiate_subelts(elt, Stream)

        obj = Field(name, attrs=attrs, aggs=aggs, procs=procs, streams=streams)

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
        processes = []

        def _collect(node):
            for child in node.children():
                if isinstance(child, Process):
                    processes.append(child)
                else:
                    _collect(child)

        _collect(self)
        return processes

