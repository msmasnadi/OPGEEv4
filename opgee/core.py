'''
.. Core OPGEE objects

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''
from pint import UnitRegistry, Quantity
import sys
from .error import OpgeeException, AbstractMethodError
from .log import getLogger
from .XMLFile import XMLFile
from .utils import coercible, resourceStream
from .stream_component import get_component_matrix, Phases

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

# Cache subclasses of Process and Technology after first call
_Process_subclasses = None
_Technology_subclasses = None

def _process_subclasses(reload=False):
    global _Process_subclasses
    if reload or _Process_subclasses is None:
        _Process_subclasses = _subclass_dict(Process)

    return _Process_subclasses

def _technology_subclasses(reload=False):
    global _Technology_subclasses
    if reload or _Technology_subclasses is None:
        _Technology_subclasses = _subclass_dict(Technology)

    return _Technology_subclasses

def process_subclass(classname, reload=False):
    d = _process_subclasses(reload=reload)
    try:
        return d[classname]
    except KeyError:
        raise OpgeeException(f"Class {classname} is not a defined subclass of Process")

def technology_subclass(classname, reload=False):
    d = _technology_subclasses(reload=reload)
    try:
        return d[classname]
    except KeyError:
        raise OpgeeException(f"Class {classname} is not a defined subclass of Technology")

# (Deprecated) Return a list of XmlInstantiable subclasses in a named module
# def xml_instantiable_classes(module_name): # e.g., 'opgee.core'
#     m = sys.modules[module_name]
#     classes = [obj for (name, obj) in m.__dict__.items() if \
#                isinstance(obj, type) and issubclass(obj, XmlInstantiable) \
#                and name != 'XmlInstantiable']
#     return classes

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

def instantiate_subelts(elt, tag, cls):
    """
    Return a list of instances of `cls` (or of its indicated subclass in the case of
    Process or Technology).

    :param elt: (lxml.etree.Element) the parent element
    :param tag: (str) the name of the subelements to find
    :param cls: (type) the class to instantiate. If cls is Process or Technology,
        the class will be that indicated instead in the element's "class" attribute.
    :return: (list) instantiated objects
    """
    objs = [cls.from_xml(e) for e in elt.findall(tag)]
    return objs


# Top of hierarchy, because this is often useful...
class OpgeeObject():
    pass


class ClassAttributes(OpgeeObject):
    """
    Support for parsing attributes.xml
    """
    def __init__(self, elt):
        super().__init__()

        class_attr = elt.attrib.get('class')
        self.class_name = class_attr or elt.tag
        self.element_name = elt.tag

        self.group_dict = {}    # key is group name; value is list of attribute names in group
        self.option_dict = {}   # key is name of <Options> group; value is dict of opt_num : opt_desc
        self.attr_dict = {}     # key is attribute name; value is instance of class 'A'

        group_elts = elt.findall('Group')   # so far, only in Field elements, but this may change
        group_dict = self.group_dict
        attr_dict  = self.attr_dict
        option_dict = self.option_dict

        # add attributes to the attr_dict from a list of XML <A> elements
        def _add_attrs(a_elts):
            for elt in a_elts:
                attr_dict[elt_name(elt)] = A.from_xml(elt)

        # add attributes defined within <Group> elements
        for group_elt in group_elts:
            group_name = elt_name(group_elt)
            elts = group_elt.findall('A')
            _add_attrs(elts)
            group_dict[group_name] = [elt_name(e) for e in elts]

        # add top-level attributes
        elts = elt.findall('A')
        _add_attrs(elts)

        # add all <Option> elements beneath elt (may be within <Group> or not)
        options_elts = elt.xpath('.//Options')
        for options_elt in options_elts:
            opts_name = elt_name(options_elt)
            opt_elts = options_elt.findall('Option')
            option_dict[opts_name] = [(e.attrib['number'], e.text) for e in opt_elts]  # TBD: store number as int?

    def group(self, name=None):
        return self.group_dict[name] if name else self.group_dict.keys()

    def option(self, name=None):
        return self.option_dict[name] if name else self.option_dict.keys()

    def attribute(self, name=None):
        return self.attr_dict[name] if name else self.attr_dict.keys()


class Attributes(OpgeeObject):
    """
    Parse and provide access to attributes.xml metadata file.
    """
    def __init__(self):
        super().__init__()
        self.classes = None  # will be dict: key is class name: Field, Process's or Technology's class; value is ClassAttributes instance

        stream = resourceStream('etc/attributes.xml', stream_type='bytes', decode=None)
        attr_xml = XMLFile(stream, schemaPath='etc/attributes.xsd')
        root = attr_xml.tree.getroot()

        # TBD: merge user's definitions into standard ones
        # user_attr_file = getParam("OPGEE.UserAttributesFile")
        # if user_attr_file:
        #     user_attr_xml = XMLFile(user_attr_file, schemaPath='etc/attributes.xsd')
        #     user_root = user_attr_xml.tree.getroot()
        #

        class_attrs = [ClassAttributes(elt) for elt in root]
        d = {obj.class_name : obj for obj in class_attrs}
        self.classes = d

    def class_attrs(self, classname, raise_error=True):
        """
        Return the ClassAttributes instance for the named class. If not found: if
        `raise_error` is True, a KeyError will be raised; if `raise_error` is False,
        None will be returned.

        :param classname: (str) the name of the class to find attributes for
        :param raise_error: (bool) whether failure to find class should raise an error
        :raises: KeyError if `raise_error` is True and classname is not in the dict.
        :return: (ClassAttributes) the instance defining attributes for classname.
        """
        return self.classes[classname] if raise_error else self.classes.get(classname)


class XmlInstantiable(OpgeeObject):
    """
    This is the superclass for all classes that are instantiable from XML. The requirements of
    such classes are:

    1. They subclass from XmlInstantiable or its subclasses
    2. They define ``__init__(self, name, **kwargs)`` and call ``super().__init__(name)``
    3. They define @classmethod from_xml(cls, element) to create an instance from XML.
    4. Subclasses of Technology also implement a run() method to perform the required operation.

    """
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.enabled = True

    @classmethod
    def from_xml(cls, elt):
        raise AbstractMethodError(cls, 'XmlInstantiable.from_xml')

    def __str__(self):
        type_str = type(self).__name__
        return f'<{type_str} name="{self.name}">'

    def is_enabled(self):
        return self.enabled

    def set_enabled(self, value):
        self.enabled = value

# to avoid redundant reporting
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
        name   = a['name']
        number = coercible(a['number'], int)

        temp = subelt_value(elt, 'Temperature', coerce=float)
        pres = subelt_value(elt, 'Pressure',    coerce=float)

        src  = a['src']
        dst  = a['dst']

        obj = Stream(name, number, temp=temp, pressure=pres, src=src, dst=dst)
        comps = obj.components

        # Set the stream component info
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


class Container(XmlInstantiable):
    """
    Generic hierarchical node element, has a name and contains subclasses of
    itself, recursively. Subclasses add attributes to those defined in superclass.
    """
    def __init__(self, name):
        super().__init__(name)
        self.emissions = None       # TBD: decide whether to cache or compute on the fly

    # default is no-op
    def run(self, level, **kwargs):
        raise AbstractMethodError(type(self), 'Container.run')

    def print_running_msg(self, level):
        print(level * '  ' + f"Running {type(self)} name='{self.name}'")

    def children(self):
        raise AbstractMethodError(type(self), 'Container.children')

    # Subclass should call this before or after local processing
    def run_children(self, level, **kwargs):
        if self.is_enabled():
            level += 1
            for child in self.children():
                child.run_children(level, **kwargs)  # depth first
                child.run(level, **kwargs)           # run self after running children

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


class Process(Container):
    def __init__(self, name, attrs=None, subprocs=None, techs=None):
        super().__init__(name)
        self.attrs = attrs
        self.subprocs = subprocs
        self.techs = techs

    def children(self):
        return self.subprocs + self.techs

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Process> element
        :return: (Process) instance populated from XML
        """
        name = elt_name(elt)

        classname = elt.attrib.get('class')
        if classname:
            print(f"found <Process class={classname}>")
        cls = Process if classname is None else process_subclass(classname)

        if cls is None:
            print(f"cls for {classname} is None")

        procs = instantiate_subelts(elt, 'Process', Process)
        techs = instantiate_subelts(elt, 'Technology', Technology)

        # TBD: fill in Smart Defaults here, or assume they've been filled already?
        attrs = instantiate_subelts(elt, 'A', A)

        obj = cls(name, attrs=attrs, subprocs=procs, techs=techs)
        return obj

    def run(self, level, **kwargs):
        """
        Run all sub-processes, passing variables, settings, and streams for the parent field.

        :param kwargs: (dict) keyword arguments
        :return:
        """
        self.print_running_msg(level)


class Technology(Container):
    def __init__(self, name, attrs=None):
        super().__init__(name)
        self.attrs = attrs

    # TBD: consider using multiple inheritance and a parent class 'Runnable' that both
    # TBD: Technology and Process inherit from.
    def children(self):
        # Although Technology is nominally a container, it has no children.
        return []

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Technology> element
        :return: (Technology) instance populated from XML
        """
        name = elt_name(elt)
        classname = elt.attrib['class']         # required
        cls = technology_subclass(classname)

        # TBD: fill in Smart Defaults here, or assume they've been filled already?
        attrs = instantiate_subelts(elt, 'A', A)

        obj = cls(name, attrs=attrs)
        return obj

    def run(self, level, **kwargs):
        """
        Run all sub-processes, passing variables, settings, and streams for the parent field.

        :param kwargs: (dict) keyword arguments
        :return:
        """
        self.print_running_msg(level)


class Field(Container):

    def __init__(self, name, attrs=None, procs=None, techs=None, streams=None):
        super().__init__(name)

        self.streams = streams
        self.attrs = attrs
        self.procs = procs
        self.techs = techs

    def children(self):
        return self.procs + self.techs

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Field> element
        :return: (Field) instance populated from XML
        """
        name = elt_name(elt)

        # TBD: fill in Smart Defaults here, or assume they've been filled already?
        attrs = instantiate_subelts(elt, 'A', A)

        procs   = instantiate_subelts(elt, 'Process', Process)
        techs   = instantiate_subelts(elt, 'Technology', Technology)
        streams = instantiate_subelts(elt, 'Stream', Stream)

        obj = Field(name, attrs=attrs, procs=procs, techs=techs, streams=streams)
        return obj

    def run(self, level, **kwargs):
        """
        Run all stages

        :param kwargs:
        :return:
        """
        self.print_running_msg(level)


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
        self.fields     = fields

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
        fields = instantiate_subelts(elt, 'Field', Field)

        obj = Analysis(name, functional_unit=fn_unit, energy_basis=en_basis, fields=fields)
        return obj

    def run(self, level, **kwargs):
        """
        Run all fields, passing variables and settings.

        :param kwargs:
        :return:
        """
        self.print_running_msg(level)


class Model(Container):
    # __attributes__ = [Attr('children', childTag='Analysis')]

    def __init__(self, name, analysis):
        super().__init__(name)
        self.analysis = analysis

    def children(self):
        return [self.analysis]      # TBD: might have a list of analyses if it's useful

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Model> element
        :return: (Model) instance populated from XML
        """
        analyses = instantiate_subelts(elt, 'Analysis', Analysis)
        count = len(analyses)
        if count != 1:
            raise OpgeeException(f"Expected on <Analysis> element; got {count}")

        obj = Model(elt_name(elt), analyses[0])
        return obj

    def run(self, **kwargs):
        """
        Run all fields, passing variables and settings.

        :param kwargs:
        :return:
        """
        print(f"Running {type(self)} name='{self.name}'")
        level = 0
        self.run_children(level+1, **kwargs)


# TBD: grab a path like OPGEE.UserClassPath, which defaults to OPGEE.ClassPath
# TBD: split these and load all *.py files in each directory (if a directory;
# TBD: allow specify specific files in path as well)
# TBD: import these into this module so they're found by class_from_str()?
# TBD: Alternatively, create dict of base classname and actual module it's in
# TBD: by looping over sys.modules[name]
class ModelFile(XMLFile):
    """
    Represents the overall parameters.xml file.
    """
    def __init__(self, filename, stream=None):
        # We expect a single 'Analysis' element below Model
        _logger.debug("Loading model file: %s", filename)

        super().__init__(stream or filename, schemaPath='etc/opgee.xsd')

        self.root = self.tree.getroot()
        self.model = Model.from_xml(self.root)
