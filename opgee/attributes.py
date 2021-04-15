"""
.. OPGEE Attribute and related classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from .core import OpgeeObject, A, elt_name
from .utils import resourceStream
from .log import getLogger
from .XMLFile import XMLFile

_logger = getLogger(__name__)

class ClassAttributes(OpgeeObject):
    """
    Support for parsing attributes.xml metadata
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
        self.classes = None  # will be dict: key is class name: Field, Aggregator, or Process's class; value is ClassAttributes instance

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
