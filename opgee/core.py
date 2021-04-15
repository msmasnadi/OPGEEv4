'''
.. Core OPGEE objects

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''
from pint import UnitRegistry, Quantity
import sys
from .error import OpgeeException, AbstractMethodError, AbstractInstantiationError
from .log import getLogger
from .utils import coercible, resourceStream
from .stream_component import get_component_matrix

_logger = getLogger(__name__)

# Note that we probably will define some of our own units:
# From a file:
# ureg.load_definitions('/your/path/to/my_def.txt')
#
# Or one at a time:
# ureg.define('dog_year = 52 * day = dy')
ureg = UnitRegistry()
ureg.load_definitions(resourceStream('etc/opgee_units.txt'))

def superclass(cls):
    """
    Get the first superclass of the given class from the __mro__ (method resolution order).
    This is necessary since super().xml_attrs() did not work as required for class methods.

    :param cls: (class) The class to get the superclass of
    :return: (class) The first superclass in class's MRO, if any, else None
    """
    mro = cls.__mro__
    return mro[1] if len(mro) > 1 else None

def class_from_str(classname, module_name=__name__):
    m = sys.modules[module_name]   # get the module object

    try:
        cls = getattr(m, classname)

        if not issubclass(cls, XmlInstantiable):
            raise OpgeeException(f'Class {classname} is not a subclass of XmlInstantiable')

        return cls

    except AttributeError:
        raise OpgeeException(f'Class {classname} is not a defined OPGEE class')

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

def get_subclass(cls, subclass_name, reload=False):
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

    valid = _Subclass_dict.keys()
    if cls not in valid:
        valid = list(valid) # expand iterator
        raise OpgeeException(f"lookup_subclass: cls {cls} must be one of {valid}")

    d = _Subclass_dict[cls]
    try:
        return d[subclass_name]
    except KeyError:
        raise OpgeeException(f"Class {subclass_name} is not a known subclass of {cls}")

def subelt_value(elt, tag, coerce=None, with_unit=True, required=True):
    """
    Get the value from the text of the named subelement of `elt`. If `required`
    is True and the element is not found, raise an error. If not found and `required`
    is False, return None. Regardless of `required`, an error is raised if multiple
    subelements with `tag` are found.

    :param elt: (etree.Element) the parent element
    :param tag: (str) the tag of the subelement
    :param coerce: (type) a type to coerce the value
    :param with_unit: (bool) if True, return a Value instance with value and unit.
    :param required: (bool) whether to raise an error if element is not found,
           or if found and `with_unit` is True, there is no unit attribute.
    :return: (str) the value found in the subelement, converted by `coerce` if
           `coerce` is not None, or if `with_unit` is True, an instance of Value.
    :raises: OpgeeException if `required` is True and the subelement isn't found,
           or if multiple subelements with `tag` are found, or if a required element
           is missing a unit attribute and `with_unit` is True.
    """
    subs = elt.findall(tag)
    count = len(subs)
    if count == 0 and not required:
        return None

    if count != 1:
        raise OpgeeException(f"Expected one {tag} subelements below {elt}; found {count}")

    subelt = subs[0]
    value = subelt.text if coerce is None else coercible(subelt.text, coerce)
    unit = subelt.attrib.get('unit')

    if with_unit:
        if unit is None:
            raise OpgeeException(f"subelt_value: unit is missing from element {subelt}")
        return Quantity(value, ureg[unit])
    else:
        return value

def elt_name(elt):
    return elt.attrib.get('name')

def instantiate_subelts(elt, cls, as_dict=False):
    """
    Return a list of instances of `cls` (or of its indicated subclass of Process).

    :param elt: (lxml.etree.Element) the parent element
    :param cls: (type) the class to instantiate. If cls is Process, the class will
        be that indicated instead in the element's "class" attribute.
    :param as_dict: (bool) if True, return a dictionary of subelements, keyed by name
    :return: (list) instantiated objects
    """
    tag = cls.__name__      # class name matches element name
    objs = [cls.from_xml(e) for e in elt.findall(tag)]

    if as_dict:
        d = {obj.name : obj for obj in objs}
        return d
    else:
        return objs

# Top of hierarchy, because it's useful to know which classes are "ours"
class OpgeeObject():
    pass


class Resource(OpgeeObject):
    """
    Resource is an abstract superclass with subclasses Reservoir and Environment. Like Processes,
    Resources can be connected to Streams, however Resources are passive; they have no "run"
    function. All Streams connected to a given Resource are inputs in the case of Environment, or
    outputs in the case of Reservoirs.
    """
    def __init__(self, name):
        if type(self) == Resource:
            raise AbstractInstantiationError(type(self))

        super().__init__()
        self.name = name
        self._streams = []

    def add_stream(self, stream):
        """
        Add a stream to a Resources stream list.

        :param stream: (Stream) the stream to add
        :return: None
        """
        self._streams.append(stream)

    def streams(self):
        return self._streams


class Reservoir(Resource):
    """
    Reservoir represents natural resources such as oil and gas reservoirs, and water sources.
    """
    def __init__(self, name):
        super().__init__(name)


class Environment(Resource):
    """
    Represents the environment, which in OPGEE is just a sink for emissions. The Environment
    has only inputs (no outputs) and can be the destination (but not source) of streams. This
    restriction would need to change if air-capture of CO2 were introduced into the model.
    Each Analysis object holds a single Environment instance.
    """
    def __init__(self):
        super().__init__('Environment')


class XmlInstantiable(OpgeeObject):
    """
    This is the superclass for all classes that are instantiable from XML. The requirements of
    such classes are:

    1. They subclass from XmlInstantiable or its subclasses
    2. They define ``__init__(self, name, **kwargs)`` and call ``super().__init__(name)``
    3. They define @classmethod from_xml(cls, element) to create an instance from XML.
    4. Subclasses of Container and Process implement run(self) to perform any required operations.

    """
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.enabled = True
        self.parent = None

    @classmethod
    def from_xml(cls, elt):
        raise AbstractMethodError(cls, 'XmlInstantiable.from_xml')

    def __str__(self):
        type_str = type(self).__name__
        name_str = f' name="{self.name}"' if self.name else ''
        return f'<{type_str}{name_str}>'

    def is_enabled(self):
        return self.enabled

    def set_enabled(self, value):
        self.enabled = value

    def adopt(self, objs):
        """
        Set the `parent` of each object to self. This is used to create back pointers
        up the hieararchy so Processes and Streams can find their Field and Analysis
        containers.

        :param objs: (None or list of XmlInstantiable)
        :return: (list) If objs is None, returns and empty list, otherwise returns
           the original objs list.
        """
        objs = [] if objs is None else objs

        for obj in objs:
            obj.parent = self

        return objs

    def find_parent(self, cls):
        """
        Ascend the parent links until an object of class `cls` is found, or
        an object with a parent that is None.

        :param cls: (type) the class of the parent sought
        :return: (XmlInstantiable or None) the desired parent instance or None
        """
        if type(self) == cls:
            return self

        if self.parent is None:
            return None

        return self.parent.find_parent(cls) # recursively ascend the graph


# to avoid redundantly reporting bad units
_undefined_units = {}

def validate_unit(unit):
    if not unit:
        return None

    if unit in ureg:
        return ureg[unit]

    if unit not in _undefined_units:
        _logger.warn(f"Unit '{unit}' is not in the UnitRegistry")
        _undefined_units[unit] = 1

    return None

# The <A> element
class A(XmlInstantiable):
    def __init__(self, name, value=None, atype=None, option_set=None, unit=None):
        super().__init__(name)

        if atype is not None:
            value = coercible(value, atype)

        unit_obj = validate_unit(unit)
        self.value = value if unit_obj is None else Quantity(value, unit_obj)

        self.option_set = option_set        # the name of the option set, if any
        self.unit = unit
        self.atype = atype

    def __str__(self):
        type_str = type(self).__name__

        attrs = f"name='{self.name}' type='{self.atype}' value='{self.value}'"

        if self.unit:
            attrs += f"unit = '{self.unit}'"

        if self.option_set:
            attrs += f" options='{self.option_set}'"

        return f"<{type_str} {attrs}>"

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing an <A> element
        :return: (A) instance of class A
        """
        a = elt.attrib

        if elt.text is None:
            from lxml import etree
            elt_xml = etree.tostring(elt).decode()
            raise OpgeeException(f"Empty <A> elements are not allowed: {elt_xml}")

        obj = A(a['name'], value=elt.text, atype=a.get('type'), unit=a.get('unit'),
                option_set=a.get('options'))

        return obj

#
# Can streams have emissions (e.g., leakage) or is that attributed to a process?
#
class Stream(XmlInstantiable):
    __instances__ = {}      # track all instances in dict keyed by stream number

    def __init__(self, name, number, temp=None, pressure=None, src=None, dst=None):
        super().__init__(name)

        prior = self.__instances__.get(number)
        if prior:
            raise OpgeeException(f"Redefinition of stream number {number}, previously defined as {prior}")

        self.__instances__[number] = self       # store in instance dictionary

        self.number = number
        self.temperature = temp
        self.pressure = pressure
        self.src = src
        self.dst = dst
        self.components = get_component_matrix()

    def __str__(self):
        return f"<Stream name='{self.name}' number={self.number} src='{self.src}' dst='{self.dst}'>"

    def component(self, name, phase=None):
        """
        Return one or all of the values for stream component `name`.

        :param name: (str) The name of a stream component
        :param phase: (str; one of {'solid', 'liquid', 'gas')
        :return:
        """
        return self.components.loc[name] if phase is None \
            else self.components.loc[name, phase]

    @classmethod
    def instances(cls):
        return cls.__instances__.values()

    @classmethod
    def find(cls, number):
        """
        Return the Stream instance with the given number, or None if not found.

        :param number: (int) the stream number
        :return: (Stream) the corresponding instance
        """
        return cls.__instances__.get(number)

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Stream> element
        :return: (Stream) instance of class Stream
        """
        a = elt.attrib
        name = a['name']
        src  = a['src']
        dst  = a['dst']
        number = coercible(a['number'], int)

        temp = subelt_value(elt, 'Temperature', coerce=float)
        pres = subelt_value(elt, 'Pressure',    coerce=float)

        obj = Stream(name, number, temp=temp, pressure=pres, src=src, dst=dst)
        comps = obj.components # allocated empty; filled in below

        # Set up the stream component info
        comp_elts = elt.findall('Component')
        for comp_elt in comp_elts:
            a = comp_elt.attrib
            comp_name = elt_name(comp_elt)
            rate  = coercible(comp_elt.text, float)
            phase = a['phase']  # required by XML schema to be one of the 3 legal values
            unit  = a['unit']   # required by XML schema (TBD: use this)

            if comp_name not in comps.index:
                raise OpgeeException(f"Unrecognized stream component name '{comp_name}'.")

            # TBD: integrate units via pint and pint_pandas
            comps.loc[comp_name, phase] = rate

        return obj


class Process(XmlInstantiable):
    """
    The "leaf" node in the container/process hierarchy. Actual runnable Processes are
    subclasses of Process, defined either in processes.py or in the user's specified files.
    """
    def __init__(self, name, inputs=None, outputs=None, attr_dict=None):
        super().__init__(name or self.__class__.__name__)
        self.attr_dict = attr_dict or {}

        self.inputs  = inputs or []     # ids (name or number) of input streams
        self.outputs = outputs or []    # ids (name or number) of output streams

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
        classname = elt.attrib['class']  # required by opgee.xsd schema
        cls = get_subclass(Process, classname)

        # TBD: fill in Smart Defaults here, or assume they've been filled already?
        attr_dict = instantiate_subelts(elt, A, as_dict=True)

        obj = cls(name, attr_dict=attr_dict)
        return obj


class Container(XmlInstantiable):
    """
    Generic hierarchical node element, has a name and contains other Containers and/or
    Processes (and subclasses thereof).
    """
    def __init__(self, name, attrs=None, aggs=None, procs=None):
        super().__init__(name)
        self.emissions = None       # TBD: decide whether to cache or compute on the fly
        self.attrs = attrs          # TBD: are any attributes necessary for containers?
        self.aggs  = self.adopt(aggs)
        self.procs = self.adopt(procs)

    def run(self, level=0, **kwargs):
        # raise AbstractMethodError(type(self), 'Container.run')
        if self.is_enabled():
            self.print_running_msg(level)
            self.run_children(level, **kwargs)
            self.summarize()

    def children(self):
        return self.aggs + self.procs

    def print_running_msg(self, level):
        print(level * '  ' + f"Running {type(self)} name='{self.name}'")

    def run_children(self, level=0, **kwargs):
        level += 1
        for child in self.children():
            child.run(level=level, **kwargs)

        # TBD: else self.bypass()?

    def summarize(self):
        # Do something at the container level after running all children
        pass

    def compute_ins_outs(self):
        """
        Method to compute inputs and outputs for this Container, which is
        computed as the inputs of child processes that are not bound to
        streams for all leaf process nodes. Something like that.

        :return: None
        """
        pass

    def aggregate_flows(self):
        """
        Compute total flows into and out of this container by summing those from
        the contained objects. Results are stored in the container. (Cached? Dynamic?)

        :return: None
        """
        pass


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


class Field(Container):
    # TBD: can a field have any Processes that are not within Aggregator nodes?
    def __init__(self, name, attrs=None, aggs=None, procs=None, streams=None):
        super().__init__(name, attrs=attrs, aggs=aggs, procs=procs)

        self.streams = streams or []
        self.environment = Environment()    # TBD: Environment per Field or per Analysis?
        self.reservoir = Reservoir("Oil")   # TBD: how much flexibility is needed here?

        # Set back pointers to this instance of Field

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


class Analysis(Container):
    def __init__(self, name, functional_unit=None, energy_basis=None,
                 variables=None, settings=None, streams=None, fields=None):
        super().__init__(name)

        # Global settings
        self.functional_unit = functional_unit
        self.energy_basis = energy_basis
        self.variables = variables   # dict of standard variables
        self.settings  = settings    # user-controlled settings
        self.streams   = streams     # define these here to avoid passing separately?
        self.fields    = self.adopt(fields)

    def children(self):
        return self.fields

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Analysis> element
        :return: (Analysis) instance populated from XML
        """
        name = elt_name(elt)
        fn_unit  = subelt_value(elt, 'FunctionalUnit', with_unit=False) # schema requires one of {'oil', 'gas'}
        en_basis = subelt_value(elt, 'EnergyBasis', with_unit=False)    # schema requires one of {'LHV', 'HHV'}
        fields = instantiate_subelts(elt, Field)

        # TBD: variables and settings
        obj = Analysis(name, functional_unit=fn_unit, energy_basis=en_basis, fields=fields)
        return obj
