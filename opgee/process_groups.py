from collections import OrderedDict
from .core import XmlInstantiable, elt_name, instantiate_subelts
from .error import OpgeeException
from .log import getLogger
from .utils import getBooleanXML

_logger = getLogger(__name__)


class ProcessChoice(XmlInstantiable):
    """
    Contains a set of mutually-exclusive `ProcessGroups`.
    """
    def __init__(self, name, groups, extend, default):
        super().__init__(name)

        self.extend = extend
        self.default = default

        # store the groups in a dict for fast lookup, maintaining order for display
        self.groups_dict = OrderedDict()
        for group in groups:
            self.groups_dict[group.name] = group

    def group_names(self):
        names = list(self.groups_dict.keys())
        return names

    def get_group(self, name, raiseError=True):
        group = self.groups_dict.get(name)
        if group is None and raiseError:
            raise OpgeeException(f"Process choice '{name}' not found in field '{self.name}'")

        return group

    # def _after_init(self):
    #     self.field = self.get_field()

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Process> element
        :return: (Process) instance populated from XML
        """
        name = elt_name(elt)

        a = elt.attrib
        extend = getBooleanXML(a.get('extend', 'false'))
        default = a.get('default')

        groups = instantiate_subelts(elt, ProcessGroup)

        obj = ProcessChoice(name, groups, extend, default)
        return obj


class ProcessGroup(XmlInstantiable):
    """
    Contains a set of `ProcessRef` and `StreamRef` instances defining one coherent
    choice of Processes.
    """
    def __init__(self, name, process_refs, stream_refs):
        super().__init__(name)

        self.process_refs = process_refs
        self.stream_refs = stream_refs

    def processes_and_streams(self):
        """
        Return a tuple of process and stream references
        :return: (tuple of lists of str)
        """
        return (self.process_refs, self.stream_refs)

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Process> element
        :return: (Process) instance populated from XML
        """
        name = elt_name(elt)
        process_refs = [elt_name(node) for node in elt.findall('ProcessRef')]
        stream_refs  = [elt_name(node) for node in elt.findall('StreamRef')]

        return ProcessGroup(name, process_refs, stream_refs)

#
# Deprecated. Probably doesn't require a class, just the string name.
#
# class ProcessRef(XmlInstantiable):
#     """
#     Names a `Process` to include in a `ProcessGroup`.
#     """
#     def __init__(self, name):
#         super().__init__(name)
#
#
# class StreamRef(XmlInstantiable):
#     """
#     Names a `Stream` to include in a `ProcessGroup`.
#     """
#     def __init__(self, name):
#         super().__init__(name)
