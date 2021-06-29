"""
.. OPGEE Attribute and related classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from collections import defaultdict
import pandas as pd
import pint_pandas
from . import ureg
from .core import OpgeeObject, XmlInstantiable, A, instantiate_subelts, elt_name, validate_unit, magnitude
from .error import OpgeeException, AttributeError
from .log import getLogger
from .pkg_utils import resourceStream
from .XMLFile import XMLFile
from .utils import coercible

_logger = getLogger(__name__)

class Options(XmlInstantiable):
    def __init__(self, name, default, options):
        super().__init__(name)
        self.default = default
        self.options = options

    @classmethod
    def from_xml(cls, elt):
        option_elts = elt.findall('Option')
        options = [(elt.text, elt.attrib.get('label', elt.text), elt.attrib.get('desc')) for elt in option_elts]
        obj = Options(elt_name(elt), elt.attrib.get('default'), options)
        return obj

class AttrDef(XmlInstantiable):
    def __init__(self, name, value=None, pytype=None, option_set=None, unit=None,
                 constraints=None, exclusive=None, synchronized=None):
        super().__init__(name)
        self.default = None
        self.option_set = option_set        # the name of the option set, if any
        self.unit = unit
        self.pytype = pytype
        self.constraints = constraints      # range constraints
        self.synchronized = synchronized
        self.exclusive = exclusive

        if value is not None:               # if value is None, we set default later
            self.set_default(value)

    def set_default(self, value):
        if self.pytype is not None:
            value = coercible(value, self.pytype)

        unit_obj = validate_unit(self.unit)

        self.default = value if unit_obj is None else ureg.Quantity(value, unit_obj)

    def __str__(self):
        type_str = type(self).__name__

        attrs = f"name='{self.name}' type='{self.pytype}' default='{self.default}'"

        if self.unit:
            attrs += f"unit = '{self.unit}'"

        if self.option_set:
            attrs += f" options='{self.option_set}'"

        return f"<{type_str} {attrs}>"

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing an <AttrDef> element
        :return: (AttrDef) instance of class AttrDef
        """
        a = elt.attrib

        ops = ('GT', 'GE', 'LT', 'LE')
        constraints = [(op, coercible(a[op], float)) for op in ops if a.get(op)]

        # if elt.text is None, we supply the default later in __init__()
        obj = AttrDef(a['name'],
                      value=elt.text,
                      pytype=a.get('type'),
                      unit=a.get('unit'),
                      option_set=a.get('options'),
                      constraints=constraints,
                      exclusive=a.get('exclusive'),
                      synchronized=a.get('synchronized'))
        return obj


class ClassAttrs(XmlInstantiable):
    """
    Support for parsing attributes.xml metadata
    """
    def __init__(self, name, attr_dict, option_dict):
        super().__init__(name)
        self.attr_dict = attr_dict
        self.option_dict = option_dict

        self.syncs = syncs = defaultdict(list)
        self.excludes = excludes = defaultdict(list)

        # Set defaults for attributes using options to the option's default
        for attr in attr_dict.values():
            set_name = attr.option_set
            if attr.default is None and set_name:
                option_set = option_dict[set_name]
                attr.set_default(option_set.default) # handles type coercion

            if attr.synchronized:
                syncs[attr.synchronized].append(attr.name)

            if attr.exclusive:
                excludes[attr.exclusive].append(attr.name)

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing an <ClassAttrs> element
        :return: (ClassAttrs) instance of class ClassAttrs
        """
        # add attributes to attr_dict from <AttrDef> elements
        attr_dict = instantiate_subelts(elt, AttrDef, as_dict=True)

        # ensure that the constraints specified in the XML are met
        cls.check_constraints(attr_dict)

        # Add all <Option> elements beneath elt to option_dict.
        option_dict = instantiate_subelts(elt, Options, as_dict=True)

        obj = cls(elt_name(elt), attr_dict, option_dict)
        return obj

    @classmethod
    def check_constraints(cls, attr_dict):
        """
        Check that all (exclusive, synchronized) constraints specified in the XML
        are, in fact, met. Otherwise raise an error.

        :param attr_dict: (dict) All the attributes for the specified class.
        :return: none
        :raises: OpgeeException if any constraints aren't met
        """
        # build constraint sets
        syncs = defaultdict(list)
        excludes = defaultdict(list)

        for attr in attr_dict.values():
            if attr.synchronized:
                syncs[attr.synchronized].append(attr)

            if attr.exclusive:
                excludes[attr.exclusive].append(attr)




    @staticmethod
    def _lookup(obj, dict_name, key, raiseError=True):
        """
        Find the value for `key` in dictionary `obj`.

        :param obj: (dict) the dictionary to operate on
        :param dict_name: (str) the name to use in error string when raising exception
        :param key: (str) the dictionary key to lookup
        :param raiseError: (bool) whether to raise an error if `key` is not found
        :return: the value associated with `key`
        :raises: OpgeeException if `key` is not present and `raiseError` is True
        """
        value = obj.get(key)
        if value is None and raiseError:
            raise AttributeError(dict_name, key)

        return value

    def attribute(self, name, raiseError=True):
        return self._lookup(self.attr_dict, 'definition', name, raiseError=raiseError)


class AttrDefs(OpgeeObject):
    """
    Parse and provide access to attributes.xml metadata file.
    This is a singleton class: use AttrDefs.get_instance() rather
    than calling AttrDefs() directly.
    """
    instance = None

    def __init__(self):
        super().__init__()

        # Will be dict: key is class name: Model, Analysis, Field, Aggregator, or Process's class.
        # Value is a ClassAttrs instance.
        self.classes = None

        _logger.debug("Reading etc/attributes.xml")
        stream = resourceStream('etc/attributes.xml', stream_type='bytes', decode=None)
        attr_xml = XMLFile(stream, schemaPath='etc/attributes.xsd')
        root = attr_xml.tree.getroot()

        # TBD: merge user's definitions into standard ones
        # user_attr_file = getParam("OPGEE.UserAttributesFile")
        # if user_attr_file:
        #     user_attr_xml = XMLFile(user_attr_file, schemaPath='etc/attributes.xsd')
        #     user_root = user_attr_xml.tree.getroot()
        #

        self.classes = instantiate_subelts(root, ClassAttrs, as_dict=True)

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = AttrDefs()

        return cls.instance

    def class_attrs(self, classname, raiseError=True):
        """
        Return the ClassAttrs instance for the named class. If not found: if
        `raise_error` is True, a KeyError will be raised; if `raise_error` is False,
        None will be returned.

        :param classname: (str) the name of the class to find attributes for
        :param raiseError: (bool) whether failure to find class should raise an error
        :return: (ClassAttrs) the instance defining attributes for classname.
        :raises: OpgeeError if `raiseError` is True and classname is not in the dict.
        """
        attrs = self.classes.get(classname)
        if attrs is None and raiseError:
            raise OpgeeException(f"class_attrs: classname {classname} is unknown.")

        return attrs


class AttributeMixin():
    """
    Consolidates attribute-related code shared by `Container` and `Process` classes.
    Note: must be mixed into classes that have both self.attr_dict and self.attr_defs.
    """

    def __init__(self):
        self.attr_dict = None

    def attr(self, attr_name, raiseError=False):
        obj = self.attr_dict.get(attr_name)
        if obj is None and raiseError:
            raise OpgeeException(f"Attribute '{attr_name}' not found in {self}")

        return obj.value if obj else None

    def set_attr(self, attr_name, value):
        obj = self.attr_dict.get(attr_name)
        if obj is None:
            raise OpgeeException(f"Attribute '{attr_name}' not found in {self}")

        obj.set_value(value)

    def attrs_with_prefix(self, prefix):
        """
        Collect a group of similarly-prefixed attributes into a dictionary keyed by the
        portion of the name after the prefix.

        :param prefix: (str) a common prefix shared by multiple attributes
        :return: (dict) attribute objects keyed by the portion of the name after the prefix.
        """
        prefix_len = len(prefix)
        attr_dict = self.attr_dict

        names = [name for name in attr_dict.keys() if name.startswith(prefix)]

        # assume that all have same units
        unit = attr_dict[names[0]].unit
        dtype = f"pint[{unit}]" if unit else None

        d = {name[prefix_len:] : attr_dict[name].value for name in names}
        s = pd.Series(d, dtype=dtype)
        return s

    # TBD: fill in Smart Defaults here, or assume they've been filled already?
    @classmethod
    def instantiate_attrs(cls, elt):
        attr_defs = AttrDefs.get_instance()
        attr_dict = {}

        # TBD:   To avoid an import loop, we don't import Process from process.py. This
        # TBD:   works, but it's a bit of a hack. There might be a better way...
        if str(cls.__mro__[1]) == "<class 'opgee.process.Process'>":
            attr_defs = AttrDefs.get_instance()
            # i.e., isinstance(cls, Process)
            process_attrs = attr_defs.classes.get('Process')
        else:
            process_attrs = None

        classname = cls.__name__
        class_attrs = attr_defs.class_attrs(classname, raiseError=False)

        if class_attrs or process_attrs:
            # Create a list of tuples of (name, value) to set attribute values below.
            user_values = {elt_name(a) : a.text for a in elt.findall('A')}

            # first copy Process attributes, if relevant. Then overwrite with subprocess attributes
            combined_dict = process_attrs.attr_dict.copy() if process_attrs else {}
            if class_attrs:
                combined_dict.update(class_attrs.attr_dict)

            unknown_attrs = set(user_values.keys()) - set(combined_dict.keys())
            if unknown_attrs:
                raise OpgeeException(f"Attributes {unknown_attrs} in model XML for '{classname}' lack metadata")

            # set up all attributes with default values
            for name, attr_def in combined_dict.items():
                user_value = user_values.get(name)
                value = user_value or attr_def.default
                attr_dict[name] = A(name, value=value, pytype=attr_def.pytype, unit=attr_def.unit)

        return attr_dict

    @classmethod
    def check_attr_constraints(cls, attr_dict):
        attr_defs = AttrDefs.get_instance()
        class_attrs = attr_defs.class_attrs(cls.__name__, raiseError=False)

        if class_attrs is None or attr_dict is None:
            return  # nothing to check

        funcs = {
            'LT': lambda value, limit: value <  limit,
            'LE': lambda value, limit: value <= limit,
            'GT': lambda value, limit: value >  limit,
            'GE': lambda value, limit: value >= limit,
        }

        def is_a_process(cls):
            for superclass in cls.__mro__:
                if superclass.__name__ == 'Process':
                    return True

            return False

        process_attr_dict = attr_defs.class_attrs('Process').attr_dict

        # Check numeric constraints
        for attr_name, attr in attr_dict.items():
            # If the definition of an attribute of a subprocess is not known, look at Process's attributes
            attr_def = class_attrs.attr_dict.get(attr_name) or (is_a_process(cls) and process_attr_dict.get(attr_name))
            if not attr_def:
                raise OpgeeException(f"Attribute '{attr_name}' not found for class '{cls.__name__}'")

            constraints = attr_def.constraints

            if constraints:
                for op, limit in constraints:
                    value = magnitude(attr.value)
                    # print(f"Testing ({value} {op} {limit}) for attr {attr_name}")
                    if not funcs[op](value, limit):
                        raise OpgeeException(f"Attribute '{attr_name}': constraint failed: value {value} is not {op} {limit}")

        # Check exclusive groups
        for group, attr_names in class_attrs.excludes.items():
            values = [attr_dict[attr_name].value for attr_name in attr_names]

            if sum(values) not in (0, 1):
                raise OpgeeException(f"Exclusive attribute group '{group}' has multiple items selected")

        # Check synchronized groups
        for group, attr_names, in class_attrs.syncs.items():
            values = [attr_dict[attr_name].value for attr_name in attr_names]
            if sum(values[1:]) != values[0]:
                raise OpgeeException(f"Attributes in synchronized group '{group}' have differing values")
