from .core import elt_name, subelt_text, instantiate_subelts
from .container import Container
from .field import Field
from .log import getLogger

_logger = getLogger(__name__)

class Analysis(Container):
    def __init__(self, name, attr_dict=None, fields=None):
        super().__init__(name, attr_dict=attr_dict)
        self.field_dict = self.adopt(fields, asDict=True)

    def get_field(self, name):
        return self.field_dict.get(name)

    def _children(self):
        """
        Return a list of all children. External callers should use children() instead,
        as it respects the self.is_enabled() setting.
        """
        return self.field_dict.values()     # N.B. returns an iterator

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Analysis> element
        :return: (Analysis) instance populated from XML
        """
        name = elt_name(elt)
        attr_dict = cls.instantiate_attrs(elt)
        fields = instantiate_subelts(elt, Field)

        obj = Analysis(name, attr_dict=attr_dict, fields=fields)
        return obj
