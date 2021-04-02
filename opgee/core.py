'''
.. Core OPGEE objects

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''
import sys
from .error import OpgeeException
from .log import getLogger
from .XMLFile import XMLFile
from .utils import coercible

_logger = getLogger(__name__)

#
# TBD: Each class should also know how to emit its equivalent XML.
# TBD: We should be able to drive this off attribute metadata as well.
#

# TBD: This works for core classes, but not for plugin-defined Process and Technology classes
def class_from_str(classname, module_name=__name__):
    m = sys.modules[module_name]   # get the module object

    try:
        cls = getattr(m, classname)

        if not issubclass(cls, XmlInstantiable):
            raise OpgeeException(f'Class {classname} is not a subclass of XmlInstantiable')

        return cls

    except AttributeError:
        raise OpgeeException(f'Class {classname} is not a defined OPGEE class')

# Return a list of XmlInstantiable subclasses in a named module
def xml_instantiable_classes(module_name): # e.g., 'opgee.core'
    m = sys.modules[module_name]
    classes = [obj for (name, obj) in m.__dict__.items() if \
               isinstance(obj, type) and issubclass(obj, XmlInstantiable) \
               and name != 'XmlInstantiable']
    return classes

#
# TBD: Make this a @classmethod to allow it to be overridden?
#
def from_xml(elt):
    """
    Instantiate a class from an XML node. The class should have the class
    attribute "_attributes_", defining how to create a class from the XML node
    of the same name.

    :param elt: (lxml Element) the one to instantiate from.
    :return: (OpgeeObject subclass) an object of the designated class
    """
    tag = elt.tag

    # Process and Technology specify the subclass to instantiate in the "class" attribute.
    # If the subclass isn't specified, instantiate the generic class.
    classname = elt.attrib.get('class', tag) if tag in ('Process', 'Technology') else tag

    cls = class_from_str(classname)

    if not issubclass(cls, XmlInstantiable):
        raise OpgeeException(f"Class {classname} is not instantiable from XML")

    name = elt.attrib.get('name', '')

    obj = cls(name)
    a_dict, c_dict  = obj.cache_xml_attr_dicts('both')

    a_nodes = elt.find('A') or []

    for node in a_nodes:
        name = node.attrib.get('name')
        attr_def = a_dict[name]

        # attempt to convert the value to the required type
        # deprecated? might *only* get values from text
        value = attr_def.atype(elt.text) if attr_def.fromText else elt.attrib.get(name, '')

        # Set the named attribute of the instantiated object to the given value
        setattr(obj, name, value)

    for child_tag, attr_def in c_dict.items():
        xpath = '|'.join(child_tag) if isinstance(child_tag, (list, tuple)) else child_tag

        child_elts = elt.xpath(xpath)

        # instantiate the children recursively
        children = [from_xml(obj, elt) for elt in child_elts]

        # Set the named attribute of obj to the list of instantiated children
        attr_def = c_dict[child_tag]
        setattr(obj, attr_def.name, children)

    return obj


def subelt_value(elt, tag, coerce=None, with_unit=True, required=True):
    """
    Get the value from the text of the named subelement of `elt`. If `required`
    is True and the element is not found, raise an error. If not found and `required`
    is False, return None. Regardless of `required`, an error is raised if multiple
    subelements with `tag` are found.

    :param elt: (etree.Element) the parent element
    :param tag: (str) the tag of the subelement
    :param coerce (type) a type to coerce the value
    :param with_unit (bool) if True, return a Value instance with value and unit.
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
        return Value(value, unit)
    else:
        return value

def elt_name(elt):
    return elt.attrib['name']

def instantiate_subelts(elt, tag, cls):
    objs = [cls.from_xml(e) for e in elt.findall(tag)]
    return objs

def superclass(cls):
    """
    Get the first superclass of the given class from the __mro__ (method resolution order).
    This is necessary since super().xml_attrs() did not work as required for class methods.

    :param cls: (class) The class to get the superclass of
    :return: (class) The first superclass in class's MRO, if any, else None
    """
    mro = cls.__mro__
    return mro[1] if len(mro) > 1 else None


# def reqd_attr(elt, name, atype=str):
#     value = elt.attrib.get(name)
#     if value is None:
#         raise OpgeeException(f"Required attribute '{name}' is missing from {elt}")
#
#     try:
#         value = atype(value)
#         return value
#     except:
#         raise OpgeeException(f"Failed to convert value '{value}' to type {atype} for attribute {name} of {elt}")


# Top of hierarchy, because this is often useful...
class OpgeeObject():
    pass


class Value(OpgeeObject):
    """
    Simple struct to combine a value and unit
    """
    __slots__ = ['value', 'unit']

    def __init__(self, value, unit):
        super().__init__()
        self.value = value
        self.unit = unit


class XmlInstantiable(OpgeeObject):
    """
    This is the superclass for all classes that are instantiable from XML. The requirements of
    such classes are:
    1. They subclass from XmlInstantiable or its subclasses
    2. They define __init__(self, name, **kwargs) and call super().__init__(name)
    3. They define @classmethod from_xml(cls, element) to create an instance from XML.
    4. Subclasses of Technology also implement a run() method to perform the required operation.
    """
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.enabled = True

    @classmethod
    def from_xml(cls, elt):
        raise OpgeeException(f'Called abstract method XmlInstantiable.from_xml() -- {cls} is missing this required method.')

    def __str__(self):
        return f'<{type(self)} name="{self.name}">'

    def is_enabled(self):
        return self.enabled

    def set_enabled(self, value):
        self.enabled = value


# The <A> element
class A(XmlInstantiable):
    def __init__(self, name, value=None, atype=None, unit=None):
        super().__init__(name)

        if atype is not None:
            value = coercible(value, atype)

        self.value = Value(value, unit)

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing an <A> element
        :return: (A) instance of class A
        """
        attr = elt.attrib

        obj = A(attr['name'], value=elt.text, atype=attr.get('type'), unit=attr.get('unit'))
        return obj

#
# Can streams have emissions (e.g., leakage) or is that attributed to a process?
#
class Stream(XmlInstantiable):
    def __init__(self, name, number, temp=None, pressure=None, src=None, dst=None, components=None):
        super().__init__(name)

        self.number = number
        self.temperature = temp
        self.pressure = pressure
        self.src = src
        self.dst = dst
        self.components = components

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Stream> element
        :return: (Stream) instance of class Stream
        """
        attr = elt.attrib

        name   = attr['name']
        number = attr['number']

        temp = subelt_value(elt, 'Temperature', coerce=float)
        pres = subelt_value(elt, 'Pressure',    coerce=float)

        src = elt_name(elt.find('Source'))
        dst = elt_name(elt.find('Destination'))

        cmps = instantiate_subelts(elt, 'Component', StreamComponent)

        obj = Stream(name, number, temp=temp, pressure=pres, src=src, dst=dst, components=cmps)
        return obj


class StreamComponent(XmlInstantiable):
    def __init__(self, name, phase=None, unit=None, rate=None):
        super().__init__(name)

        self.phase = phase
        self.unit  = unit
        self.rate  = rate

    @classmethod
    def from_xml(cls, elt):
        name = elt_name(elt)
        rate  = subelt_value(elt, 'Rate', coerce=float)
        phase = subelt_value(elt, 'Phase', with_unit=False)

        obj = StreamComponent(name, phase=phase, rate=rate)
        return obj


class Container(XmlInstantiable):
    """
    Generic hierarchical node element, has a name and contains subclasses of
    itself, recursively. Subclasses add attributes to those defined in superclass.
    """
    def __init__(self, name):
        super().__init__(name)
        self.children = []
        self.emissions = None       # TBD: what to store here?

    def set_children(self, children):
        self.children = children

    # default is no-op
    def run(self, **kwargs):
        pass

    # Subclass should call this before or after local processing
    def run_children(self, **kwargs):
        if self.is_enabled():
            for child in self.children:
                child.run_children()    # depth first
                child.run(**kwargs)     # run self after running children

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


class Analysis(Container):
    def __init__(self, name, functional_unit=None, energy_basis=None):
        super().__init__(name)

        # Global settings
        self.functional_unit = functional_unit
        self.energy_basis = energy_basis

        self.variables = None   # dict of standard variables
        self.settings  = None   # user-controlled settings
        self.streams   = None   # define these here to avoid passing separately?

        # Attr('variables', childTag='Variable'),
        # Attr('settings', childTag='Setting'),
        # Attr('children', childTag='Field'),
        # Attr('streams', childTag='Stream'),     # or are these just tracked in Analysis, since streams point to their ins/outs


    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Stream> element
        :return: (Stream) instance of class Stream
        """
        name = elt_name(elt)
        fn_unit  = subelt_value(elt, 'FunctionalUnit', with_unit=False)
        en_basis = subelt_value(elt, 'EnergyBasis', with_unit=False)

        obj = Analysis(name, functional_unit=fn_unit, energy_basis=en_basis)
        return obj

    def run(self, **kwargs):
        """
        Run all fields, passing variables and settings.

        :param kwargs:
        :return:
        """
        pass


class Field(Container):
    __attr_dict__  = {}
    __child_dict__ = {}
    __attributes__ = [
        Attr('location'),
        Attr('age', atype=int, unit="y"),
        Attr('depth', unit="ft"),
        Attr('children', childTag='Process'),
        Attr('streams', childTag='Stream'),     # or are these just tracked in Analysis, since streams point to their ins/outs
    ]

    def __init__(self, name):
        super().__init__(name)

        self.location = None  # some indication of location. Lat/Long?
        self.country  = None  # where located
        self.streams  = None  # streams to or from the environment

    def run(self, **kwargs):
        """
        Run all stages

        :param kwargs:
        :return:
        """
        pass


class Process(Container):
    __attr_dict__  = {}
    __child_dict__ = {}
    __attributes__ = [
        Attr('type'),
        Attr('children', childTag=['Process', 'Technology']),
    ]

    def __init__(self, name):
        super().__init__(name)


    def run(self, **kwargs):
        """
        Run all sub-processes, passing variables, settings, and streams for the parent field.

        :param kwargs: (dict) keyword arguments
        :return:
        """
        pass


class Technology(Container):
    __attr_dict__  = {}
    __child_dict__ = {}
    __attributes__ = [
        Attr('type'),
    ]

    def __init__(self, name):
        super().__init__(name)

    def run(self, **kwargs):
        """
        Run all sub-processes, passing variables, settings, and streams for the parent field.

        :param kwargs: (dict) keyword arguments
        :return:
        """
        pass


class Model(Container):
    __attr_dict__  = {}
    __child_dict__ = {}
    __attributes__ = [
        Attr('children', childTag='Analysis')
    ]

    def __init__(self, name):
        super().__init__(name)


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
    def __init__(self, filename):
        super().__init__(filename, schemaPath='etc/opgee.xsd')

        root = self.tree.getroot()

        # We expect a single 'Analysis' element below Model

        _logger.debug("Loaded model file: %s", filename)

def create_model(xml_path):
    m = XMLFile(xml_path, schemaPath='etc/opgee.xsd')
    root = m.tree.getroot()   # the outermost <Model> element
    model = from_xml(None, root)

