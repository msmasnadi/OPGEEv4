"""
.. OPGEE Model and ModelFile classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from . import ureg
from .analysis import Analysis
from .container import Container
from .core import instantiate_subelts, elt_name
from .config import getParam
from .error import OpgeeException
from .field import Field
from .log import getLogger
from .process import reload_subclass_dict
from .stream import Stream
from .table_manager import TableManager
from .utils import loadModuleFromPath, splitAndStrip
from .XMLFile import XMLFile

_logger = getLogger(__name__)


class Model(Container):

    def __init__(self, name, analyses, fields, attr_dict=None):
        super().__init__(name, attr_dict=attr_dict)

        Model.instance = self

        self.analysis_dict = self.adopt(analyses, asDict=True)
        self.field_dict = self.adopt(fields, asDict=True)

        self.table_mgr = tbl_mgr = TableManager()

        # load all the GWP options
        df = tbl_mgr.get_table('GWP')

        self.gwp_horizons = list(df.Years.unique())
        self.gwp_versions = list(df.columns[2:])
        self.gwp_dict = {y: df.query('Years == @y').set_index('Gas', drop=True).drop('Years', axis='columns') for y in
                         self.gwp_horizons}

        df = tbl_mgr.get_table('constants')
        self.constants = {name: ureg.Quantity(float(row.value), row.unit) for name, row in df.iterrows()}

        self.process_EF_df = tbl_mgr.get_table("process-specific-EF")

        self.water_treatment = tbl_mgr.get_table("water-treatment")

        self.heavy_oil_upgrading = tbl_mgr.get_table("heavy-oil-upgrading")

        self.transport_share_fuel = tbl_mgr.get_table("transport-share-fuel")

        self.mining_energy_intensity = tbl_mgr.get_table("bitumen-mining-energy-intensity")

        self.prod_combustion_coeff = tbl_mgr.get_table("product-combustion-coeff")
        self.reaction_combustion_coeff = tbl_mgr.get_table("reaction-combustion-coeff")

        self.gas_turbine_tbl = tbl_mgr.get_table("gas-turbine-specs")

        self.gas_dehydration_tbl = tbl_mgr.get_table("gas-dehydration")
        self.AGR_tbl = tbl_mgr.get_table("acid-gas-removal")
        self.ryan_holmes_process_tbl = tbl_mgr.get_table("ryan-holmes-process")
        self.demethanizer = tbl_mgr.get_table("demethanizer")

        # TBD: should these be settable per Analysis?
        # parameters controlling process cyclic calculations
        self.maximum_iterations = self.attr('maximum_iterations')
        self.maximum_change = self.attr('maximum_change')

        self.pathname = None  # set by calling set_pathname(path)

    def _after_init(self):
        for obj in self.fields():
            obj._after_init()

        for obj in self.analyses():
            obj._after_init()

    def set_pathname(self, pathname):
        self.pathname = pathname

    def fields(self):
        return self.field_dict.values()

    def analyses(self):
        return self.analysis_dict.values()

    def get_analysis(self, name, raiseError=True):
        analysis = self.analysis_dict.get(name)
        if analysis is None and raiseError:
            raise OpgeeException(f"Analysis named '{name}' is not defined")

        return analysis

    def get_field(self, name, raiseError=True):
        field = self.field_dict.get(name)
        if field is None and raiseError:
            raise OpgeeException(f"Field named '{name}' is not defined in Model")

        return field

    def const(self, name):
        """
        Return the value of a constant declared in tables/constants.csv

        :param name: (str) name of constant
        :return: (float with unit) value of constant
        """
        try:
            return self.constants[name]
        except KeyError:
            raise OpgeeException(f"No known constant with name '{name}'")

    def _children(self, include_disabled=False):
        """
        Return a list of all children objects. External callers should use children()
        instead, as it respects the self.is_enabled() setting.
        """
        return self.analyses()  # N.B. returns an iterator

    def summarize(self):
        """
        Return a summary of energy use and emissions, by Model, Field, Aggregator, and Process.

        :return: TBD: Unclear what the best structure for this is; it depends how it will be used.
        """
        pass

    def validate(self):
        # TBD: validate all attributes of classes Field, Process, etc.
        pass

        # show_streams = False
        #
        # if show_streams:
        #     for field in self.fields():
        #         print(f"Processes for field {field.name}")
        #         for proc in field.processes():
        #             print(f"  {proc}")
        #
        #         print(f"\nStreams for field {field.name}")
        #         for stream in field.streams():
        #             print(f"  {stream}")
        #
        #     print("")

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Model> element
        :return: (Model) instance populated from XML
        """
        analyses = instantiate_subelts(elt, Analysis)
        fields = instantiate_subelts(elt, Field)
        attr_dict = cls.instantiate_attrs(elt)

        obj = Model(elt_name(elt), analyses, fields, attr_dict=attr_dict)

        # do stuff that requires the fully instantiated hierarchy
        obj._after_init()

        return obj


class ModelFile(XMLFile):
    """
    Represents the overall parameters.xml file.
    """

    def __init__(self, filename, stream=None, add_stream_components=True, use_class_path=True):
        """
        Several steps are performed, some of which are dependent on the function's parameters:

        1. If `add_stream_components` is True, load any extra stream components defined by config file
        variable "OPGEE.StreamComponents".

        2. Reads the input XML filename using either from `filename` (if `stream` is None) or from
        `stream`. In the latter case, the filename is used only as a description of the stream.

        3. If `use_class_path` is True, loads any Python files found in the path list defined by
        "OPGEE.ClassPath". Note that all classes referenced by the XML must be defined internally
        by opgee, or in the user's files indicated by "OPGEE.ClassPath".

        4. Construct the model data structure from the input XML file and store the result in `self.model`.

        :param filename: (str) the name of the file to read, if `stream` is None, else the description
           of the file, e.g., "[opgee package]/etc/opgee.xml".
        :param stream: (file-like object) if not None, read from this stream rather than opening `filename`.
        """
        import os
        from pathlib import Path

        if add_stream_components:
            extra_components = getParam('OPGEE.StreamComponents')
            if extra_components:
                names = splitAndStrip(extra_components, ',')
                Stream.extend_components(names)

        # We expect a single 'Analysis' element below Model
        _logger.debug("Loading model file: %s", filename)

        super().__init__(stream or filename, schemaPath='etc/opgee.xsd')

        if use_class_path:
            class_path = getParam('OPGEE.ClassPath')
            paths = [Path(path) for path in class_path.split(os.path.pathsep) if path]
            for path in paths:
                if path.is_dir():
                    for module_path in path.glob('*.py'):  # load all .py files found in directory
                        loadModuleFromPath(module_path)
                else:
                    loadModuleFromPath(path)

            reload_subclass_dict()

        self.root = self.tree.getroot()
        self.model = Model.from_xml(self.root)

        # If we're reading a stream, we'll show that in the GUI
        self.model.set_pathname(str(stream) if stream else filename)
        self.model
