"""
.. OPGEE Model and ModelFile classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from .core import Analysis, Container, instantiate_subelts, elt_name
from .attributes import Attributes
from .error import OpgeeException
from .log import getLogger
from .XMLFile import XMLFile

_logger = getLogger(__name__)


class Model(Container):
    def __init__(self, name, analysis):
        super().__init__(name)
        self.analysis = analysis

    def children(self):
        return [self.analysis]      # TBD: might have a list of analyses if it's useful

    def validate(self):

        # TBD: validate all attributes of classes Field, Process, etc.
        attributes = Attributes()
        field_attrs = attributes.class_attrs('Field')

        # print(field_attrs.attribute('downhole_pump'))
        # print(field_attrs.attribute('ecosystem_richness'))
        # print(field_attrs.option('ecosystem_C_richness'))

        # Collect all processes defined for each field
        for field in self.analysis.fields:
            procs = field.collect_processes()
            print(f"Processes for field {field.name}")
            for proc in procs:
                print(f"  {proc}")

            print(f"\nStreams for field {field.name}")
            for stream in field.streams:
                print(f"  {stream}")

        print("")


    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Model> element
        :return: (Model) instance populated from XML
        """
        analyses = instantiate_subelts(elt, Analysis)
        count = len(analyses)
        if count != 1:
            raise OpgeeException(f"Expected on <Analysis> element; got {count}")

        obj = Model(elt_name(elt), analyses[0])
        return obj

    def run(self, **kwargs):
        """
        Run all fields, passing variables and settings.

        :param kwargs:
        :return:
        """
        print(f"Running {type(self)} name='{self.name}'")
        level = 0
        self.run_children(level+1, **kwargs)


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
    def __init__(self, filename, stream=None):
        # We expect a single 'Analysis' element below Model
        _logger.debug("Loading model file: %s", filename)

        super().__init__(stream or filename, schemaPath='etc/opgee.xsd')

        self.root = self.tree.getroot()
        self.model = Model.from_xml(self.root)
