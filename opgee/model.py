"""
.. OPGEE Model and ModelFile classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from . import ureg
from .analysis import Analysis
from .container import Container
from .core import instantiate_subelts, elt_name
from .attributes import AttrDefs
from .config import getParam, unixPath
from .error import OpgeeException, XmlFormatError
from .field import Field
from .log import getLogger
from .pkg_utils import resourceStream
from .process import reload_subclass_dict
from .stream import Stream
from .table_manager import TableManager
from .utils import loadModuleFromPath, splitAndStrip
from .XMLFile import XMLFile
from .xml_utils import merge_elements, save_xml

DEFAULT_SCHEMA_VERSION = "4.0.0.a"

_logger = getLogger(__name__)

class Model(Container):

    def __init__(self, name, analyses, fields, attr_dict=None):
        super().__init__(name, attr_dict=attr_dict)

        Model.instance = self

        self.schema_version = attr_dict.get('schema_version', DEFAULT_SCHEMA_VERSION)

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

        self.transport_parameter = tbl_mgr.get_table("transport-parameter")
        self.transport_share_fuel = tbl_mgr.get_table("transport-share-fuel")
        self.transport_by_mode = tbl_mgr.get_table("transport-by-mode")

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

        self.pathnames = None  # set by calling set_pathnames(path)

    def _after_init(self):
        for obj in self.fields():
            obj._after_init()

        for obj in self.analyses():
            obj._after_init()

    def set_pathnames(self, pathnames):
        self.pathnames = pathnames

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

