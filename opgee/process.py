'''
.. OPGEE process support

.. Copyright (c) 2021 Richard Plevin and Adam Brandt
   See the https://opensource.org/licenses/MIT for license details.
'''
from .core import A, Container, XmlInstantiable, elt_name, instantiate_subelts
from .error import OpgeeException, AbstractMethodError
from .stream import Stream
from .utils import getBooleanXML

def _subclass_dict(superclass):
    """
    Return a dictionary of all defined subclasses of `superclass`, keyed by name.
    Does not descent beyond immediate subclasses.

    :return: (dict) subclasses keyed by name
    """
    d = {cls.__name__ : cls for cls in superclass.__subclasses__()}
    return d

#
# Cache of known subclasses of Aggregator and Process
#
_Subclass_dict = None

def _get_subclass(cls, subclass_name, reload=False):
    """
    Return the class for `subclass_name`, which must be a known subclass of `cls`.

    :param cls: (type) the class (Process or Aggregator) for which we're finding a subclass.
    :param subclass_name: (str) the name of the subclass
    :param reload: (bool) if True, reload the cache of subclasses of `cls`.
    :return: (type) the class object
    :raises: OpgeeException if `cls` is not Process or Aggregator or if the subclass is not known.
    """
    global _Subclass_dict

    if reload or _Subclass_dict is None:
        _Subclass_dict = {
            Aggregator : _subclass_dict(Aggregator),
            Process    : _subclass_dict(Process)
        }

    subclasses = _Subclass_dict.keys()
    if cls not in subclasses:
        raise OpgeeException(f"lookup_subclass: cls {cls} must be one of {list(subclasses)}")

    d = _Subclass_dict[cls]
    try:
        return d[subclass_name]
    except KeyError:
        raise OpgeeException(f"Class {subclass_name} is not a known subclass of {cls}")


class Process(XmlInstantiable):
    """
    The "leaf" node in the container/process hierarchy. Actual runnable Processes are
    subclasses of Process, defined either in processes.py or in the user's specified files.
    """
    def __init__(self, name, desc=None, consumes=None, produces=None, attr_dict=None):
        name = name or self.__class__.__name__
        super().__init__(name)

        self.desc = desc or name
        self.attr_dict = attr_dict or {}

        self.produces = set(produces) if produces else {}
        self.consumes = set(consumes) if consumes else {}

        self.extend = False
        self.field = None               # the Field we're part of, set on first lookup

        self.inputs  = []              # Stream instances, set in Field.connect_processes()
        self.outputs = []              # ditto

    def get_field(self):
        """
        Find and cache the Field instance that contains this Process

        :return: (Field) the enclosing Field instance
        """
        if not self.field:
            self.field = self.find_parent('Field')

        return self.field

    def find_stream(self, name, raiseError=False):
        """
        Convenience function to find a named stream from a Process instance by calling
        find_stream() on the enclosing Field instance.

        :param name: (str) the name of the Stream to find
        :param raiseError: (bool) whether to raise an error if the Stream is not found.
        :return: (Stream or None) the requested stream, or None if not found and `raiseError` is False.
        :raises: OpgeeException if `name` is not found and `raiseError` is True
        """
        field = self.get_field()
        return field.find_stream(name, raiseError=raiseError)

    def find_input_streams(self, stream_type, combine=False, raiseError=True):
        """
        Find the input streams connected to an upstream Process that handles the indicated
        `stream_type`, e.g., 'crude oil', 'raw water' and so on.

        :param direction: (str) 'input' or 'output'
        :param stream_type: (str) the generic type of stream a process can handle.
        :param combine: (bool) whether to (thermodynamically) combine multiple Streams into a single one
        :param raiseError: (bool) whether to raise an error if no handlers of `stream_type` are found.
        :return: (Stream or list of Streams) if `combine` is True, a single, combined stream is returned,
           otherwise a list of Streams.
        :raises: OpgeeException if no processes handling `stream_type` are found and `raiseError` is True
        """
        streams = [stream for stream in self.inputs if stream.dst_proc.handles(stream_type)]
        if not streams and raiseError:
            raise OpgeeException(f"{self}: no input streams connect to processes handling '{stream_type}'")

        return Stream.combine(streams) if combine else streams

    def handles(self, stream_type):
        return stream_type in self.consumes

    def find_output_streams(self, stream_type, raiseError=True):
        """
        Find the output streams connected to a downstream Process that handles the indicated
        `stream_type`, e.g., 'crude oil', 'raw water' and so on.

        :param direction: (str) 'input' or 'output'
        :param stream_type: (str) the generic type of stream a process can handle.
        :param raiseError: (bool) whether to raise an error if no handlers of `stream_type` are found.
        :return: (list of Streams)
        :raises: OpgeeException if no processes handling `stream_type` are found and `raiseError` is True
        """
        streams = [stream for stream in self.outputs if stream.dst_proc.handles(stream_type)]
        if not streams and raiseError:
            raise OpgeeException(f"{self}: no output streams connect to processes handling '{stream_type}'")

        return streams

    def add_output_stream(self, stream):
        self.outputs.append(stream)

    def add_input_stream(self, stream):
        self.inputs.append(stream)

    def set_extend(self, extend):
        self.extend = extend

    def run_internal(self, level, **kwargs):
        """
        This method implements the behavior required of the Process subclass, when
        the Process is enabled. If it is disabled, the run() method calls bypass()
        instead. **Subclasses of Process must implement this method.**

        :param level: (int) nesting level; used to indent diagnostic output
        :param kwargs: (dict) arbitrary keyword args passed down from the Analysis object.
        :return: None
        """
        raise AbstractMethodError(type(self), 'Process.run_internal')

    def run(self, level, **kwargs):
        """
        If the Process is enabled, calls self.run_internal() else call self.bypass().

        :param level: (int) nesting level; used to indent diagnostic output
        :param kwargs: (dict) arbitrary keyword args passed down from the Analysis object.
        :return: None
        """
        if not self.enabled:
            self.bypass()
        else:
            self.run_internal(level, **kwargs)

    # TBD: Can we create a generic method for passing inputs to outputs when disabled?
    # TBD: If not, this will become an abstract method.
    def bypass(self):
        pass

    #
    # The next two methods are provided to allow Aggregator to call children() and
    # run_children() without type checking. For Processes, these are just no-ops.
    #
    def children(self):
        return []

    def run_children(self, level, **kwargs):
        pass

    def print_running_msg(self, level):
        print(level * '  ' + f"Running {type(self)} name='{self.name}'")

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Process> element
        :return: (Process) instance populated from XML
        """
        name = elt_name(elt)
        a = elt.attrib
        desc = a.get('desc')

        classname = a['class']  # required by XML schema
        subclass = _get_subclass(Process, classname)

        # TBD: fill in Smart Defaults here, or assume they've been filled already?
        attr_dict = instantiate_subelts(elt, A, as_dict=True)

        produces = [node.text for node in elt.findall('Produces')]
        consumes = [node.text for node in elt.findall('Consumes')]

        obj = subclass(name, desc=desc, attr_dict=attr_dict, produces=produces, consumes=consumes)

        obj.set_enabled(getBooleanXML(a.get('enabled', '1')))
        obj.set_extend(getBooleanXML(a.get('extend', '0')))

        return obj

class Reservoir(Process):
    """
    Reservoir represents natural resources such as oil and gas reservoirs, and water sources.
    Each Field object holds a single Reservoir instance.
    """
    def run(self, level, **kwargs):
        self.print_running_msg(level)

class Environment(Process):
    """
    Represents the environment, which in OPGEE is just a sink for emissions. The Environment
    has only inputs (no outputs) and can be the destination (but not source) of streams. This
    restriction might change if air-capture of CO2 were introduced into the model. Each Analysis
    object holds a single Environment instance.
    """
    def __init__(self):
        super().__init__('Environment', desc='The Environment')

    def run(self, level, **kwargs):
        self.print_running_msg(level)


class Aggregator(Container):
    def __init__(self, name, attrs=None, aggs=None, procs=None):
        super().__init__(name, attrs=attrs, aggs=aggs, procs=procs)

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Aggregator> element
        :return: (Aggregator) instance populated from XML
        """
        name = elt_name(elt)

        aggs  = instantiate_subelts(elt, Aggregator)
        procs = instantiate_subelts(elt, Process)

        # TBD: fill in Smart Defaults here, or assume they've been filled already?
        attrs = instantiate_subelts(elt, A)

        obj = cls(name, attrs=attrs, aggs=aggs, procs=procs)
        return obj
