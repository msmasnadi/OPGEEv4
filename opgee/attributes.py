"""
.. OPGEE Attribute and related classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from pint import Quantity
from .core import OpgeeObject, XmlInstantiable, instantiate_subelts, elt_name, validate_unit
from .error import OpgeeException
from .log import getLogger
from .pkg_utils import resourceStream
from .XMLFile import XMLFile
from .utils import coercible

_logger = getLogger(__name__)

class Attr(XmlInstantiable):
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

        :param elt: (etree.Element) representing an <Attr> element
        :return: (Attr) instance of class Attr
        """
        a = elt.attrib

        if elt.text is None:
            from lxml import etree
            elt_xml = etree.tostring(elt).decode()
            raise OpgeeException(f"Empty <A> elements are not allowed: {elt_xml}")

        obj = Attr(a['name'], value=elt.text, atype=a.get('type'), unit=a.get('unit'),
                   option_set=a.get('options'))
        return obj


class Class(XmlInstantiable):
    """
    Support for parsing attributes.xml metadata
    """
    def __init__(self, name, attr_dict, option_dict):
        super().__init__(name)
        self.attr_dict = attr_dict
        self.option_dict = option_dict

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing an <Class> element
        :return: (Class) instance of class Class
        """
        # add attributes to attr_dict from <Attr> elements
        attr_dict = instantiate_subelts(elt, Attr, as_dict=True)

        # Add all <Option> elements beneath elt to option_dict. Key is name
        # of <Options> set; value is dict of (opt_num, opt_desc)
        option_dict = {}
        for options_elt in elt.findall('Options'):
            opts_name = elt_name(options_elt)
            opt_elts = options_elt.findall('Option')
            option_dict[opts_name] = [(e.attrib['number'], e.text) for e in opt_elts]  # TBD: store number as int?

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


class AttributeDefs(OpgeeObject):
    """
    Parse and provide access to attributes.xml metadata file.
    """
    def __init__(self):
        super().__init__()

        # Will be dict: key is class name: Model, Analysis, Field, Aggregator, or Process's class.
        # Value is ClassAttributeDefs instance.
        self.classes = None

        stream = resourceStream('etc/attributes.xml', stream_type='bytes', decode=None)
        attr_xml = XMLFile(stream, schemaPath='etc/attributes.xsd')
        root = attr_xml.tree.getroot()

        # TBD: merge user's definitions into standard ones
        # user_attr_file = getParam("OPGEE.UserAttributesFile")
        # if user_attr_file:
        #     user_attr_xml = XMLFile(user_attr_file, schemaPath='etc/attributes.xsd')
        #     user_root = user_attr_xml.tree.getroot()
        #

        self.classes = instantiate_subelts(root, Class, as_dict=True)

    def class_attrs(self, classname, raiseError=True):
        """
        Return the ClassAttributeDefs instance for the named class. If not found: if
        `raise_error` is True, a KeyError will be raised; if `raise_error` is False,
        None will be returned.

        :param classname: (str) the name of the class to find attributes for
        :param raiseError: (bool) whether failure to find class should raise an error
        :return: (ClassAttributeDefs) the instance defining attributes for classname.
        :raises: OpgeeError if `raiseError` is True and classname is not in the dict.
        """
        attrs = self.classes.get(classname)
        if attrs is None and raiseError:
            raise OpgeeException(f"class_attrs: classname {classname} is unknown.")

        return attrs

    def attr_def(self, classname, name, raiseError=True):
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
