#
# Core OPGEE objects
#
# Author: Richard Plevin
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import pint

from . import ureg
from .constants import std_temperature, std_pressure
from .error import OpgeeException, AbstractMethodError
from .log import getLogger
from .utils import coercible, getBooleanXML

_logger = getLogger(__name__)

def magnitude(value, units=None):
    """
    Return the magnitude of ``value``. If ``value`` is a ``pint.Quantity`` and
    ``units`` is not None, check that ``value`` has the expected units and
    return the magnitude of ``value``. If ``value`` is not a ``pint.Quantity``,
    just return it.

    :param value: (float or pint.Quantity) the value for which we return the magnitude.
    :param units: (None or pint.Unit) the expected units
    :return: the magnitude of `value`
    """
    if isinstance(value, ureg.Quantity):
        # if optional units are provided, validate them
        if units:
            if not isinstance(units, pint.Unit):
                units = ureg.Unit(units)
            if value.units != units:
                raise OpgeeException(f"magnitude: value {value} units are not {units}")

        return value.m
    else:
        return value


def name_of(obj):
    return obj.name


def elt_name(elt):
    return elt.attrib.get('name')


def instantiate_subelts(elt, cls, as_dict=False):
    """
    Return a list of instances of ``cls`` (or of its indicated subclass of ``Process``).

    :param elt: (lxml.etree.Element) the parent element
    :param cls: (type) the class to instantiate. If cls is Process, the class will
        be that indicated instead in the element's "class" attribute.
    :param as_dict: (bool) if True, return a dictionary of subelements, keyed by name
    :return: (list) instantiated objects
    """
    tag = cls.__name__  # class name matches element name
    objs = [cls.from_xml(e) for e in elt.findall(tag)]

    if as_dict:
        d = {obj.name: obj for obj in objs}
        return d
    else:
        return objs


def dict_from_list(objs):
    """
    Create a dictionary of ``XMLInstantiable`` objects by their name attribute, but
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


CLASS_DELIMITER = '.'

def split_attr_name(attr_name):
    splits = attr_name.split(CLASS_DELIMITER)
    count = len(splits)

    if count == 0:
        raise OpgeeException(f"Attribute name is empty")

    if count == 1:
        class_name, attr_name = None, splits[0]

    elif count == 2:
        class_name, attr_name = splits

    else:
        raise OpgeeException(f"Attribute name '{attr_name}' has more than 2 dot-delimited parts")

    return class_name, attr_name


# Top of hierarchy, because it's useful to know which classes are "ours"
class OpgeeObject():
    @classmethod
    def clear(cls):
        # Clear state stored in class variables
        pass


class XmlInstantiable(OpgeeObject):
    """
    This is the superclass for all classes that are instantiable from XML. The requirements of
    such classes are:

    1. They subclass from XmlInstantiable or its subclasses
    2. They define ``__init__(self, name, **kwargs)`` and call ``super().__init__(name)``
    3. They define ``@classmethod from_xml(cls, element)`` to create an instance from XML.
    4. Subclasses of Container and Process implement ``run(self)`` to perform any required operations.

    """

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.enabled = True
        self.parent = None

    def _after_init(self):
        pass

    @classmethod
    def from_xml(cls, elt):
        raise AbstractMethodError(cls, 'XmlInstantiable.from_xml')

    def __str__(self):
        type_str = type(self).__name__
        name_str = f' name="{self.name}"' if self.name else ''
        return f'<{type_str}{name_str} enabled={self.enabled}>'

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

        return {obj.name: obj for obj in objs} if asDict else objs

    def find_parent(self, cls):
        """
        Ascend the parent links until an object of class `cls` is found, or
        an object with a parent that is None.

        :param cls: (type or str name of type) the class of the parent sought
        :return: (XmlInstantiable or None) the desired parent instance or None
        """
        if type(self) == cls or self.__class__.__name__ == cls:
            return self

        if self.parent is None:
            return None

        return self.parent.find_parent(cls)  # recursively ascend the graph


# to avoid redundantly reporting bad units
_undefined_units = {}


def validate_unit(unit):
    """
    Return the ``pint.Unit`` associated with the string ``unit``, or ``None``
    if ``unit`` is ``None`` or not in the unit registry.

    :param unit: (str) a string representation of a ``pint.Unit``

    :return: (pint.Unit or None)
    """
    if not unit:
        return None

    if unit in ureg:
        return ureg.Unit(unit)

    if unit not in _undefined_units:
        _logger.warning(f"Unit '{unit}' is not in the UnitRegistry")
        _undefined_units[unit] = 1

    return None


class A(OpgeeObject):
    """
    The ``<A>`` element represents the value of an attribute previously defined in
    `attributes.xml` or a user-provided file. Note that this class is not instantiated
    using ``from_xml()`` approach since values are merged with metadata from `attributes.xml`.
    """

    def __init__(self, name, value=None, pytype=None, unit=None, explicit=False):
        """
        Creates an attribute instance.

        :param name: (str) the attribute name
        :param value: (str) string representation of attribute value
        :param pytype: (type) the type the value should be coerced to (plus unit)
        :param unit: (str) the attributes units
        :param explicit: (bool) whether the value was explicit in the file; if not,
          it implies the value was set from the default in the attribute definition.
        """
        super().__init__()
        self.name = name
        self.unit = unit
        self.pytype = pytype
        self.explicit = explicit
        self.value = self.set_value(value)

    def set_value(self, value):
        """
        Sets the instances' value to the value given, using the stored ``pytype`` for type
        conversion and ``unit`` to define a ``pint.Quantity``, if given.

        :param value: (str, numerical, or pint.Quantity) the value to possibly convert
        :return: the value, converted to ``pytype``, and with ``unit``, if specified.
        """
        if value is None:
            return None

        unit_obj = validate_unit(self.unit)

        if isinstance(value, pint.Quantity):
            if value.units == unit_obj:
                self.value = value
                return value
            else:
                value = value.magnitude

        if self.pytype:
            value = coercible(value, self.pytype)

        if unit_obj is not None:
            value = ureg.Quantity(value, unit_obj)

        self.value = value
        return value

    def __str__(self):
        type_str = type(self).__name__
        attrs = f"name='{self.name}' type='{self.pytype}' value='{self.value}'"

        return f"<{type_str} {attrs}>"


class TemperaturePressure(OpgeeObject):
    __slots__ = ('T', 'P')      # keeps instances small and fast

    def __init__(self, T, P):
        self.T = None
        self.P = None
        self.set(T=T, P=P)

    def __str__(self):
        return f"<T={self.T} P={self.P}>"

    def set(self, T=None, P=None):
        if T is None and P is None:
            _logger.warning("Tried to set TemperaturePressure with both values None")
            return

        if T is not None:
            self.T = T if isinstance(T, pint.Quantity) else ureg.Quantity(float(T), "degF")

        if P is not None:
            self.P = P if isinstance(P, pint.Quantity) else ureg.Quantity(float(P), "psia")

    def get(self):
        return (self.T, self.P)

    def copy_from(self, tp):
        self.set(T=tp.T, P=tp.P)

# Standard temperature and pressure
STP = TemperaturePressure(std_temperature, std_pressure)
