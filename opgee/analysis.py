import re
from .core import elt_name, OpgeeObject
from .container import Container
from .error import OpgeeException
from .emissions import Emissions
from .field import Field
from .log import getLogger
from .utils import getBooleanXML

_logger = getLogger(__name__)


class Group(OpgeeObject):
    def __init__(self, elt):
        self.is_regex = getBooleanXML(elt.attrib.get('regex', 0))
        self.text = elt.text


class Analysis(Container):
    def __init__(self, name, attr_dict=None, field_names=None, groups=None):
        super().__init__(name, attr_dict=attr_dict)

        self._field_names = field_names     # this list is extended in _after_init
        self.groups = groups

        # The following are set in _after_init()
        self.model = None
        self.field_dict = None

        # This is set in _after_init() to a pandas.Series holding the current values in use,
        # indexed by gas name. Must be set after initialization since we reference the Model
        # object which isn't fully instantiated until after we are.
        self.gwp = None


    def _after_init(self):
        self.check_attr_constraints(self.attr_dict)

        self.model = model = self.find_parent('Model')
        fields = [model.get_field(name) for name in self._field_names]

        for group in self.groups:
            text = group.text
            if group.is_regex:
                prog = re.compile(text)
                matches = [field for field in model.fields() for name in field.group_names if prog.match(name)]
            else:
                matches = [field for field in model.fields() if field.name == text]

            fields.extend(matches)

        # storing into dict eliminates duplicates
        self.field_dict = {field.name: field for field in fields}

        # Use the GWP years and version specified in XML
        gwp_horizon = self.attr('GWP_horizon')
        gwp_version = self.attr('GWP_version')

        self.use_GWP(gwp_horizon, gwp_version)

        # self.gwp_series = pd.Series({name: self.GWP(name) for name in Stream.components},
        #                             dtype="pint[frac]")

    def get_field(self, name, raiseError=True) -> Field:
        """
        Find a `Field` by name in an `Analysis`.

        :param name: (str) the name of the `Field`
        :param raiseError: (bool) whether to raise an error if the field is not found
        :return: (Field) the named field, or None if not found and `raiseError` is False.
        """
        field = self.field_dict.get(name)
        if field is None and raiseError:
            raise OpgeeException(f"Field named '{name}' is not defined in Analysis '{self.name}'")

        return field

    def fields(self):
        """
        Get the `Field`s included in this `Analysis`.
        :return: (iterator) of Field instances
        """
        return self.field_dict.values()  # N.B. returns an iterator

    def first_field(self):
        return self.get_field(self._field_names[0])

    def _children(self):
        """
        Return an iterator of all children Fields. External callers should use children() instead,
        as it respects the self.is_enabled() setting.
        """
        return self.fields()

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

    # def GWP(self, gas):
    #     """
    #     Return the GWP for the given gas, using the model's settings for GWP time horizon and
    #     the version of GWPs to use.
    #
    #     :param gas: (str) a gas for which a GWP has been defined. Current list is CO2, CO, CH4, N2O, and VOC.
    #     :return: (int) GWP value
    #     """
    #     hydrocarbons = Stream._hydrocarbons
    #     carbon_number = gas
    #     gas = carbon_to_molecule(gas) if gas in hydrocarbons else gas
    #     non_methane_hydrocarbons = Stream._non_mathane_hydrocarbons
    #
    #     if carbon_number in non_methane_hydrocarbons:
    #         result = self.gwp["VOC"]
    #     elif gas in self.gwp:
    #         result = self.gwp[gas]
    #     else:
    #         result = 0
    #     return result

    def run(self):
        """
        Run all children and collect emissions and energy use for all Containers and Processes.

        :return: None
        """
        for field in self.fields():
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
        field_names = [elt_name(node) for node in elt.findall('Field')]
        groups = [Group(node) for node in elt.findall('Group')]

        obj = Analysis(name, attr_dict=attr_dict, field_names=field_names, groups=groups)
        return obj
