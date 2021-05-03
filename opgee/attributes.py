"""
.. OPGEE Attribute and related classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from .core import OpgeeObject, XmlInstantiable, A, instantiate_subelts, elt_name, validate_unit, ureg
from .error import OpgeeException
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
        options = [(elt.text, elt.attrib.get('desc')) for elt in option_elts]
        obj = Options(elt_name(elt), elt.attrib.get('default'), options)
        return obj

class AttrDef(XmlInstantiable):
    def __init__(self, name, value=None, pytype=None, option_set=None, unit=None):
        super().__init__(name)
        self.default = None
        self.option_set = option_set        # the name of the option set, if any
        self.unit = unit
        self.pytype = pytype

        if value is not None:               # if value is None, we set default later
            self.set_default(value)

    def set_default(self, value):
        if self.pytype is not None:
            value = coercible(value, self.pytype)

        unit_obj = validate_unit(self.unit)

        self.default = value if unit_obj is None else ureg.Quantity(value, unit_obj)

    def __str__(self):
        type_str = type(self).__name__

        attrs = f"name='{self.name}' type='{self.pytype}' value='{self.value}'"

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

        # if elt.text is None, we supply the default later in __init__()
        obj = AttrDef(a['name'], value=elt.text, pytype=a.get('type'), unit=a.get('unit'),
                   option_set=a.get('options'))
        return obj


class ClassAttrs(XmlInstantiable):
    """
    Support for parsing attributes.xml metadata
    """
    def __init__(self, name, attr_dict, option_dict):
        super().__init__(name)
        self.attr_dict = attr_dict
        self.option_dict = option_dict

        # TBD: set defaults for attributes using options to the option's default
        for attr in attr_dict.values():
            set_name = attr.option_set
            if attr.default is None and set_name:
                option_set = option_dict[set_name]
                attr.set_default(option_set.default) # handles type coercion

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing an <ClassAttrs> element
        :return: (ClassAttrs) instance of class ClassAttrs
        """
        # add attributes to attr_dict from <AttrDef> elements
        attr_dict = instantiate_subelts(elt, AttrDef, as_dict=True)

        # Add all <Option> elements beneath elt to option_dict.
        option_dict = instantiate_subelts(elt, Options, as_dict=True)

        obj = cls(elt_name(elt), attr_dict, option_dict)
        return obj

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
        if key:
            value = obj.get(key)
            if value is None and raiseError:
                raise OpgeeException(f"Attribute {dict_name} named '{key}' was not found")

            return value
        else:
            return obj.keys()

    def option(self, name=None, raiseError=True):
        return self._lookup(self.option_dict, 'option', name, raiseError=raiseError)

    def attribute(self, name=None, raiseError=True):
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

    def get_def(self, classname, name, raiseError=True):
        """
        Return the definition of an attribute `name` defined for class `classname`.

        :param classname: (str) the name of a class associated with the attribute
        :param name: (str) the name of an attribute
        :param raiseError: (bool) whether to raise an error if the attribute or
           classname are not known.
        :return: the value of the attribute
        :raises: OpgeeException if the attribute or classname are unknown.
        """
        class_attrs = self.class_attrs(classname, raiseError=raiseError)
        return class_attrs.attribute(name, raiseError=raiseError)


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

        return obj.value

    def attrs_with_prefix(self, prefix):
        """
        Collect a group of similarly-prefixed attributes into a dictionary keyed by the
        portion of the name after the prefix.

        :param prefix: (str) a common prefix shared by multiple attributes
        :return: (dict) attribute objects keyed by the portion of the name after the prefix.
        """
        from pandas import Series

        prefix_len = len(prefix)
        attr_dict = self.attr_dict

        names = [name for name in attr_dict.keys() if name.startswith(prefix)]

        # assume that all have same units
        # unit = attr_dict[names[0]].unit
        dtype = None # doesn't work with custom types f"pint[{unit}]" if unit else None

        d = {name[prefix_len:] : attr_dict[name].value for name in names}
        s = Series(d, dtype=dtype)
        return s

    # TBD: fill in Smart Defaults here, or assume they've been filled already?
    @classmethod
    def instantiate_attrs(cls, elt):
        classname = cls.__name__

        attr_defs = AttrDefs.get_instance()
        attr_dict = {}

        class_attrs = attr_defs.class_attrs(classname, raiseError=False)

        if class_attrs:
            # Create a list of tuples of (name, value) to set attribute values below.
            user_values = {elt_name(a) : a.text for a in elt.findall('A')}

            if len(user_values) > 0 and class_attrs is None:
                raise OpgeeException(f"Attributes defined in model XML for {classname} lack metadata")

            # set up all attributes with default values
            for name, attr_def in class_attrs.attr_dict.items():
                user_value = user_values.get(name)
                value = user_value or attr_def.default
                attr_dict[name] = A(name, value=value, pytype=attr_def.pytype, unit=attr_def.unit)

        return attr_dict
