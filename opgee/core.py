'''
.. Core OPGEE objects

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''
from pint import UnitRegistry, Quantity
from .error import OpgeeException, AbstractMethodError, AbstractInstantiationError
from .log import getLogger
from .pkg_utils import resourceStream
from .utils import coercible, getBooleanXML

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

# deprecated
# def class_from_str(classname, module_name=__name__):
#     m = sys.modules[module_name]   # get the module object
#
#     try:
#         cls = getattr(m, classname)
#
#         if not issubclass(cls, XmlInstantiable):
#             raise OpgeeException(f'Class {classname} is not a subclass of XmlInstantiable')
#
#         return cls
#
#     except AttributeError:
#         raise OpgeeException(f'Class {classname} is not a defined OPGEE class')

def subelt_text(elt, tag, coerce=None, with_unit=True, required=True):
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

def dict_from_list(objs):
    """
    Create a dictionary of XMLInstantiable objects by their name attribute, but
    raise an error if any name is repeated.

    :param objs: (list of XMLInstantiable instances) the object to create dict from.
    :return: (dict) objects keyed by name
    :raises: OpgeeException if a any name is repeated
    """
    d = dict()
    for obj in objs:
        name = obj.name
        if d.get(name):
            classname = obj.__class__.__name__
            raise OpgeeException(f"{classname} instances must have unique names: {name} is not unique.")

        d[name] = obj

    return d

# Top of hierarchy, because it's useful to know which classes are "ours"
class OpgeeObject():
    pass


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
        enabled_str = '' if self.enabled else f' enabled="0"'
        return f'<{type_str}{name_str}{enabled_str}>'

    def is_enabled(self):
        return self.enabled

    def set_enabled(self, value):
        self.enabled = getBooleanXML(value)

    def adopt(self, objs, asDict=False):
        """
        Set the `parent` of each object to self. This is used to create back pointers
        up the hieararchy so Processes and Streams can find their Field and Analysis
        containers. Return the objects either as a list or dict.

        :param objs: (None or list of XmlInstantiable)
        :param asDict: (bool) if True, return a dict of objects keyed by their name,
            otherwise return a list of the objects.
        :return: (list) If objs is None, return an empty list or dict (per `asDict`),
            otherwise return the objs either in a list or dict.
        """
        objs = [] if objs is None else objs

        for obj in objs:
            obj.parent = self

        return {obj.name : obj for obj in objs} if asDict else objs

    def find_parent(self, cls):
        """
        Ascend the parent links until an object of class `cls` is found, or
        an object with a parent that is None.

        :param cls: (type or str, i.e., name of type) the class of the parent sought
        :return: (XmlInstantiable or None) the desired parent instance or None
        """
        if type(self) == cls or str(type(self)) == cls:
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

    def run(self, names=None, **kwargs):
        """
        Run all children of this Container if `names` is None, otherwise run only the
        children whose names are in in `names`.

        :param names: (None, or list of str) the names of children to run
        :param kwargs: (dict) arbitrary keyword args to pass through
        :return: None
        """
        if self.is_enabled():
            self.print_running_msg()
            self.run_children(names=names, **kwargs)
            self.summarize()

    def children(self):
        return self.aggs + self.procs

    def print_running_msg(self):
        print(f"Running {type(self)} name='{self.name}'")

    def run_children(self, names=None, **kwargs):
        for child in self.children():
            if names is None or child.name in names:
                child.run(**kwargs)

        # TBD: else self.bypass()?

    def summarize(self):
        # Do something at the container level after running all children
        pass
