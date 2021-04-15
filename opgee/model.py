"""
.. OPGEE Model and ModelFile classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from .core import Analysis, Container, instantiate_subelts, elt_name
from .config import getParam
from .attributes import Attributes
from .error import OpgeeException
from .log import getLogger
from .utils import resourceStream, loadModuleFromPath
from .XMLFile import XMLFile

_logger = getLogger(__name__)


class Model(Container):
    def __init__(self, name, analysis):
        super().__init__(name)

        self.analysis = analysis
        analysis.parent = self

        self.stream_table = self.read_stream_table()

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
        if False:
            for field in self.analysis.children():
                procs = field.collect_processes()
                print(f"Processes for field {field.name}")
                for proc in procs:
                    print(f"  {proc}")

                print(f"\nStreams for field {field.name}")
                for stream in field.streams:
                    print(f"  {stream}")

            print("")

    def read_stream_table(self):
        import pandas as pd

        s = resourceStream('etc/streams.csv')
        df = pd.read_csv(s, index_col='number')
        return df

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
        import os
        from pathlib import Path

        # We expect a single 'Analysis' element below Model
        _logger.debug("Loading model file: %s", filename)

        super().__init__(stream or filename, schemaPath='etc/opgee.xsd')

        class_path = getParam('OPGEE.ClassPath')
        paths = [Path(path) for path in class_path.split(os.path.pathsep) if path]
        for path in paths:
            if path.is_dir():
                for module_path in path.glob('*.py'):   # load all .py files found in directory
                    loadModuleFromPath(module_path)
            else:
                loadModuleFromPath(path)

        self.root = self.tree.getroot()
        self.model = Model.from_xml(self.root)
