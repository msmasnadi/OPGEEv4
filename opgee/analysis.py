#
# Author: Richard Plevin
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import re

from .config import getParamAsList
from .container import Container
from .core import elt_name, OpgeeObject
from .emissions import Emissions
from .error import OpgeeException
from .field import Field
from .log import getLogger
from .utils import getBooleanXML

_logger = getLogger(__name__)


class Group(OpgeeObject):
    def __init__(self, elt):
        self.is_regex = getBooleanXML(elt.attrib.get('regex', 0))
        self.text = elt.text


class Analysis(Container):
    """
    Describes a single `Analysis`, which can contain multiple `Fields`, including
    several attributes common to an analysis, including:

    - functional unit (oil or gas),

    - system boundary (e.g., Production, Distribution),

    - time horizon for GWPs (20 or 100 year), and

    - which IPCC assessment report to use for CO2-equivalence values (AR4, AR5, AR5 with C-cycle feedback, or AR6).

    See also :doc:`OPGEE XML documentation <opgee-xml>`
    """
    def __init__(self, name, parent=None, attr_dict=None, field_names=None, groups=None):
        super().__init__(name, attr_dict=attr_dict, parent=parent)
        self.check_attr_constraints(self.attr_dict)

        if not parent:
            raise OpgeeException("Tried to create Analysis without specifying parent (Model)")

        self.model = model = parent

        # self.field_dict = None
        self._field_names = field_names     # may be extended in add_children()
        self.groups = [] if groups is None else groups

        self.fn_unit = self.attr("functional_unit")
        self.boundary = self.attr("boundary")

        # Create validation sets from system.cfg to avoid hard-coding these
        self.functional_units = set(getParamAsList('OPGEE.FunctionalUnits'))

        # This is set in use_GWP() below to a pandas Series holding the current
        # values in use, indexed by gas name.
        self.gwp = None

        # Use the GWP years and version specified in XML
        gwp_horizon = self.attr('GWP_horizon')
        gwp_version = self.attr('GWP_version')

        self.use_GWP(gwp_horizon, gwp_version)

        fields = [model.get_field(name) for name in self._field_names]

        # Add to 'fields' any Field that matches Groups declared by the Analysis
        for group in self.groups:
            text = group.text
            if group.is_regex:
                prog = re.compile(text)
                matches = [field for field in model.fields() for
                           name in field.group_names if prog.match(name)]
            else:
                matches = [field for field in model.fields() if text in field.group_names]

            fields.extend(matches)
            self._field_names.extend([field.name for field in matches])

        # storing into dict eliminates duplicates
        self.field_dict = {field.name: field for field in fields}

    def restrict_fields(self, field_names):
        """
        Remove from the Analysis all Fields that are not named in ``field_names``.

        :param field_names: (list of str) the names of Fields to include
        :return: none
        """
        names = set(field_names)
        # Use list comprehension rather than set.intersection to maintain original order
        self._field_names = [name for name in self._field_names if name in names]


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
        Get the (enabled) ``Field``s included in this ``Analysis``.

        :return: (iterator) of Field instances
        """
        flds = [f for f in self.field_dict.values() if f.is_enabled()]  # N.B. returns an iterator
        return flds

    def field_names(self, enabled_only=True):
        if enabled_only:
            names = [f.name for f in self.fields()]
            return names
        else:
            return self._field_names

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
    #     non_methane_hydrocarbons = Stream._non_methane_hydrocarbons
    #
    #     if carbon_number in non_methane_hydrocarbons:
    #         result = self.gwp["VOC"]
    #     elif gas in self.gwp:
    #         result = self.gwp[gas]
    #     else:
    #         result = 0
    #     return result

    def run(self, compute_ci=True):
        """
        Run all children and collect emissions and energy use for all Containers and Processes.

        :param compute_ci: (bool) whether to compute carbon intensity for each field that is run.
        :return: None
        """
        for field in self.fields():
            field.run(self, compute_ci=compute_ci)

    def instances_by_class(self, cls):
        """
        Find one or more instances of ``cls`` known to this Analysis instance.
        If ``cls`` is ``Analysis``, just return ``self``; if ``cls`` is ``Field``,
        return all fields from our ``field_dict``.

        :param cls: (Class) the class to find
        :return: (Analysis instance or iterator of Field instances), or None if ``cls``
          is neither ``Field`` nor ``Analysis``.
        """
        if issubclass(cls, self.__class__):
            return self

        if issubclass(cls, Field):
            return self.field_dict.values()

    @classmethod
    def from_xml(cls, elt, parent=None, field_names=None):
        """
        Instantiate an instance from an XML element.

        :param elt: (etree.Element) representing a <Analysis> element
        :param parent: (opgee.Model) the Model containing the new Analysis
        :param field_names: (list[str] or None) field names to restrict to,
            otherwise all fields declared in the Analysis are used.
        :return: (Analysis) instance populated from XML
        """
        name = elt_name(elt)
        attr_dict = cls.instantiate_attrs(elt)
        field_names = field_names or [elt_name(node) for node in elt.findall('FieldRef')]
        groups = [Group(node) for node in elt.findall('Group')]

        obj = Analysis(name, attr_dict=attr_dict, parent=parent, field_names=field_names, groups=groups)
        return obj
