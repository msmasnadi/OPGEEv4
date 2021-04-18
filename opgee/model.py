"""
.. OPGEE Model and ModelFile classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from .analysis import Analysis
from .core import Container, instantiate_subelts, elt_name, subelt_text
from .config import getParam
from .error import OpgeeException
from .field import Field
from .log import getLogger
from .pkg_utils import resourceStream
from .stream import Stream
from .utils import loadModuleFromPath, splitAndStrip
from .XMLFile import XMLFile

_logger = getLogger(__name__)

class Analysis(Container):
    def __init__(self, name, functional_unit=None, energy_basis=None,
                 variables=None, settings=None, streams=None, fields=None):
        super().__init__(name)

        # Global settings
        self.functional_unit = functional_unit
        self.energy_basis = energy_basis
        self.variables = variables   # dict of standard variables
        self.settings  = settings    # user-controlled settings
        self.streams   = streams     # define these here to avoid passing separately?
        self.field_dict = self.adopt(fields, asDict=True)

    def children(self):
        return self.field_dict.values()     # N.B. returns an iterator

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Analysis> element
        :return: (Analysis) instance populated from XML
        """
        name = elt_name(elt)
        fn_unit  = subelt_text(elt, 'FunctionalUnit', with_unit=False) # schema requires one of {'oil', 'gas'}
        en_basis = subelt_text(elt, 'EnergyBasis', with_unit=False)    # schema requires one of {'LHV', 'HHV'}
        fields = instantiate_subelts(elt, Field)

        # TBD: variables and settings
        obj = Analysis(name, functional_unit=fn_unit, energy_basis=en_basis, fields=fields)
        return obj


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
        # attributes = Attributes()
        # field_attrs = attributes.class_attrs('Field')
        # print(field_attrs.attribute('downhole_pump'))
        # print(field_attrs.attribute('ecosystem_richness'))
        # print(field_attrs.option('ecosystem_C_richness'))

        show_streams = False

        if show_streams:
            for field in self.analysis.children():
                procs = field.collect_processes()
                print(f"Processes for field {field.name}")
                for proc in procs:
                    print(f"  {proc}")

                print(f"\nStreams for field {field.name}")
                for stream in field.streams():
                    print(f"  {stream}")

            print("")

    def report(self):
        pass

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

        extra_components = getParam('OPGEE.StreamComponents')
        if extra_components:
            names = splitAndStrip(extra_components, ',')
            Stream.extend_components(names)

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
