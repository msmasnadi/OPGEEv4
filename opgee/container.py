#
# OPGEE Container and Aggregator classes
#
# Author: Richard Plevin
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from .attributes import AttrDefs, AttributeMixin
from .core import XmlInstantiable
from .emissions import Emissions
from .energy import Energy
from .import_export import ImportExport
from .log import getLogger

_logger = getLogger(__name__)

class Container(XmlInstantiable, AttributeMixin):
    """
    Generic hierarchical node element, has a name and contains other Containers and/or
    Processes (and subclasses thereof).
    """
    def __init__(self, name, attr_dict=None, aggs=None, procs=None):
        super().__init__(name)

        self.attr_defs = AttrDefs.get_instance()
        self.attr_dict = attr_dict or {}

        self.emissions = Emissions()
        self.energy = Energy()
        self.import_export = ImportExport()
        self.ghgs = 0.0

        self.aggs  = self.adopt(aggs)
        self.procs = self.adopt(procs)

    def _children(self):
        """
        Return a list of all children. External callers should use children() instead,
        as it respects the self.is_enabled() setting.
        """
        objs = self.aggs + self.procs
        return objs

    def children(self, include_disabled=False):
        """
        Return all directly contained `Process` and `Container` objects below this
        `Container`. See also `self.descendant_procs()` and`self.descendant_aggs()`.

        :param include_disabled: (bool) whether to include disabled nodes.
        :return: (list of Containers and/or Processes)
        """
        objs = self._children()
        return [obj for obj in objs if (include_disabled or obj.is_enabled())]

    def descendant_procs(self, include_disabled=False):
        """
        Return all Processes contained in the current Container or its sub-Containers.

        :param include_disabled: (bool) whether to include disabled nodes.
        :return: (list of Processes)
        """
        procs = []

        def _add_children(container, include_disabled=False):
            for obj in container.children():
                if isinstance(obj, Container):
                    _add_children(obj, include_disabled=include_disabled)
                elif (include_disabled or obj.is_enabled()):
                    procs.append(obj)

        _add_children(self)
        return procs

    def descendant_aggs(self):
        """
        Return a list of all descendent `Container` instances.

        :return: (list of opgee.Container)
        """
        aggs = self.aggs.copy() if self.aggs else []

        for agg in self.aggs:  # loop over original since we're extending the copy
            aggs.extend(agg.descendant_aggs())

        return aggs

    def print_running_msg(self):
        _logger.debug(f"Running {type(self)} name='{self.name}'")

    def get_energy_rates(self):
        """
        Return the energy consumption rates by summing those of our children nodes,
        recursively working our way down the Container hierarchy, and storing each
        result at each container level.
        """
        self.energy.data[:] = 0.0
        data = self.energy.data

        for child in self.children():
            child_data = child.get_energy_rates()
            data += child_data

        return data

    def get_emission_rates(self, analysis, procs_to_exclude=None):
        """
        Return a tuple of the emission rates (Series) and the calculated GHG value (float).
        Uses the current choice of GWP values in the enclosing Model.

        :return: ((pandas.Series, float)) a tuple containing the emissions Series
            and the GHG value computed using the model's current GWP settings.
        """
        data = self.emissions.data
        data[:] = 0.0

        for child in self.children():
            if not procs_to_exclude or child not in procs_to_exclude:
                child_data = child.get_emission_rates(analysis, procs_to_exclude=procs_to_exclude)
                data += child_data

        return data

    def get_net_imported_product(self):
        """
        Return a energy rate (water is mass rate) of net imported product.
        The positive value means the amount needs imported, while the negative value mean the amount needs exported

        """
        imp_exp = self.import_export.imports_exports()
        data = imp_exp[ImportExport.NET_IMPORTS]

        for child in self.children():
            child_data = child.get_net_imported_product()
            data += child_data

        return data


