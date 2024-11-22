#
# Core OPGEE objects
#
# Author: Richard Plevin
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import pint
import time
import datetime

from . import ureg
from .error import OpgeeException, AbstractMethodError, ModelValidationError
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

def instantiate_subelts(elt, cls, parent=None, as_dict=False, include_names=None,
                        **cls_args):
    """
    Return a list of instances of ``cls`` (or of its indicated subclass of ``Process``).

    :param elt: (lxml.etree.Element) the parent element
    :param cls: (type) the class to instantiate. If cls is Process, the class will
        be that indicated instead in the element's "class" attribute.
    :param parent: (XmlInstantiable) the parent to record in each object instantiated
    :param as_dict: (bool) if True, return a dictionary of subelements, keyed by name
    :param include_names: (list of str) Names of elements to include (i.e., the element's
       attrib dict must have a "name" item, whose value is compared to the list). If
       ``include_names`` is not None, then elements with names not in the list are
       ignored.
    :param field_names: (list of str) Names of Fields to include when instantiating an Analysis.
       This is a special case to avoid loading more than the one Field being run in a worker.
    :return: (list) instantiated objects
    """
    tag = cls.__name__  # class name matches element name

    include = None if include_names is None else set(include_names)
    objs = [cls.from_xml(e, parent=parent, **cls_args)
            for e in elt.findall(tag) if include is None or e.attrib.get('name') in include]

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
    3. They define ``@classmethod from_xml(cls, element, parent=None)`` to create an instance from XML.
    4. Subclasses of Container and Process implement ``run(self)`` to perform any required operations.

    """
    def __init__(self, name, parent=None):
        super().__init__()
        self.name = name
        self.parent = parent
        self.enabled = True

    def set_parent(self, parent):
        self.parent = parent

    @classmethod
    def from_xml(cls, elt, parent=None, **cls_args):
        raise AbstractMethodError(cls, 'XmlInstantiable.from_xml')

    def __str__(self):
        type_str = type(self).__name__
        name_str = f' name="{self.name}"' if self.name else ''
        return f'<{type_str}{name_str} enabled={self.enabled}>'

    def print_in_context(self):
        """
        Print the object along with its parents, to provide context.

        :return: none
        """
        obj = self
        seq = [obj]
        while ((obj := obj.parent) is not None):
            seq.insert(0, obj)

        indent = 0
        for obj in seq:
            print("  " * indent, obj)
            indent += 1

    def is_enabled(self):
        return self.enabled

    def set_enabled(self, value):
        self.enabled = getBooleanXML(value)

    def adopt(self, objs, asDict=False):
        """
        Set the `parent` of each object to self. This is used to create back pointers
        up the hierarchy so Processes and Streams can find their Field and Analysis
        containers. Return the objects either as a list or dict.

        :param objs: (None or list of XmlInstantiable)
        :param asDict: (bool) if True, return a dict of objects keyed by their name,
            otherwise return a list of the objects.
        :return: (list) If objs is None, return an empty list or dict (per `asDict`),
            otherwise return the objs either in a list or dict.
        """
        objs = [] if objs is None else objs
        dct = {}

        for obj in objs:
            if (existing := dct.get(obj.name)):
                obj.print_in_context()
                existing.print_in_context()
                raise ModelValidationError(f"Tried to adopt {obj} which is a duplicate of {existing}.")
            dct[obj.name] = obj
            obj.set_parent(self)

        return dct if asDict else objs

    def find_container(self, cls):
        """
        Ascend the parent links in the object hierarchy until an object of class `cls`
        is found, or an object with a parent that is None.

        :param cls: (type or str name of type) the class of the parent sought
        :return: (XmlInstantiable or None) the desired parent instance or None
        """
        if type(self) == cls or self.__class__.__name__ == cls:
            return self

        if self.parent is None:
            return None

        return self.parent.find_container(cls)  # recursively ascend the graph


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

    def str_value(self):
        """
        Return the value of an attribute as a string.

        :return: (str) string representation of the attribute value
        """
        return str(self.value)

    def __str__(self):
        type_str = type(self).__name__
        attrs = f"name='{self.name}' type='{self.pytype}' value='{self.value}'"

        return f"<{type_str} {attrs}>"


class TemperaturePressure(OpgeeObject):
    """
    Stores temperature and pressure together for convenience.
    """
    __slots__ = ('T', 'P')      # keeps instances small and fast

    def __init__(self, T, P):
        self.T = None
        self.P = None
        self.set(T=T, P=P)

    def __str__(self):
        return f"<T={self.T} P={self.P}>"

    def set(self, T=None, P=None):
        if T is None and P is None:
            #_logger.warning("Tried to set TemperaturePressure with both values None")
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
std_temperature = ureg.Quantity(60.0, "degF")
std_pressure    = ureg.Quantity(14.676, "psia")
STP = TemperaturePressure(std_temperature, std_pressure)

class Timer:
    def __init__(self, feature_name, start=True):
        self.feature_name = feature_name
        self.start_time = None
        self.stop_time  = None

        if start:
            self.start()

    def start(self):
        self.start_time = time.time()
        return self

    def stop(self):
        self.stop_time = time.time()
        return self

    def duration(self):
        seconds = self.stop_time - self.start_time
        return datetime.timedelta(seconds=int(seconds))

    def __str__(self):
        if self.start_time is None:
            status = "is uninitialized"
        elif self.stop_time is None:
            status = "is running"
        else:
            d = self.duration()
            status = f"completed in {d}"

        return f"<Timer '{self.feature_name}' {status}>"

