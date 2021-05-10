from .core import elt_name
from .container import Container
from .error import OpgeeException
from .emissions import Emissions
from .field import Field
from .log import getLogger

_logger = getLogger(__name__)

class Analysis(Container):
    def __init__(self, name, attr_dict=None, fields=None, groups=None):
        super().__init__(name, attr_dict=attr_dict)

        self.model = None   # set in after_init()
        self.fields = fields
        self.groups = groups

        # This is set in after_init() to a pandas.Series holding the current values in use,
        # indexed by gas name. Must be set after initialization since we reference the Model
        # object which isn't fully instantiated until after we are.
        self.gwp = None

    def after_init(self):
        self.model = self.parent    # for clarity elsewhere in the code

        # Use the GWP years and version specified in XML
        gwp_horizon = self.attr('GWP_horizon')
        gwp_version = self.attr('GWP_version')

        self.use_GWP(gwp_horizon, gwp_version)

    def get_field(self, name, raiseError=True):
        return self.model.get_field(name, raiseError=raiseError)

    def _children(self):
        """
        Return a list of all children. External callers should use children() instead,
        as it respects the self.is_enabled() setting.
        """
        return self.field_dict.values()     # N.B. returns an iterator

    def use_GWP(self, gwp_horizon, gwp_version):
        """
        Set which GWP values to use for this model. Initially set from the XML model definition,
        but this function allows this choice to be changed after the model is loaded, e.g., by
        choosing different values in a GUI and rerunning the emissions summary.

        :param gwp_horizon: (int) the GWP time horizon; currently must 20 or 100.
        :param gwp_version: (str) the GWP version to use; must be one of 'AR4', 'AR5', 'AR5_CCF'
        :return: none
        """
        from pint import Quantity

        model = self.model

        if isinstance(gwp_horizon, Quantity):
            gwp_horizon = gwp_horizon.magnitude

        known_horizons = model.gwp_horizons
        if gwp_horizon not in known_horizons:
            raise OpgeeException(f"GWP years must be one of {known_horizons}; value given was {gwp_horizon}")

        known_versions = model.gwp_versions
        if gwp_version not in known_versions:
            raise OpgeeException(f"GWP version must be one of {known_versions}; value given was {gwp_version}")

        df = model.gwp_dict[gwp_horizon]
        gwp = df[gwp_version]
        self.gwp = gwp.reindex(index=Emissions.emissions)  # keep them in the same order for consistency

    def GWP(self, gas):
        """
        Return the GWP for the given gas, using the model's settings for GWP time horizon and
        the version of GWPs to use.

        :param gas: (str) a gas for which a GWP has been defined. Current list is CO2, CO, CH4, N2O, and VOC.
        :return: (int) GWP value
        """
        return self.gwp[gas]

    def run(self):
        """
        Run all children and collect emissions and energy use for all Containers and Processes.

        :return: None
        """
        for field_name in self.fields:
            field = self.get_field(field_name)
            field.run(self)

    @classmethod
    def from_xml(cls, elt):
        """
        Instantiate an instance from an XML element

        :param elt: (etree.Element) representing a <Analysis> element
        :return: (Analysis) instance populated from XML
        """
        name = elt_name(elt)
        attr_dict = cls.instantiate_attrs(elt)
        fields = [node.text for node in elt.findall('WithField')]
        groups = [node.text for node in elt.findall('WithGroup')]

        obj = Analysis(name, attr_dict=attr_dict, fields=fields, groups=groups)
        return obj
