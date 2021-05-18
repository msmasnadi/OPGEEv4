'''
.. OPGEE Container and Aggregator classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''
from .attributes import AttrDefs, AttributeMixin
from .core import XmlInstantiable
from .emissions import Emissions
from .energy import Energy
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
        Ignore disabled nodes unless `included_disabled` is True

        :param include_disabled: (bool) whether to include disabled nodes.
        :return: (list of Containers and/or Processes)
        """
        objs = self._children()
        return [obj for obj in objs if (include_disabled or obj.is_enabled())]

    def print_running_msg(self):
        _logger.info(f"Running {type(self)} name='{self.name}'")


    def report_energy_and_emissions(self, analysis):
        # calculate and store results internally
        self.get_energy_rates(analysis)
        self.get_emission_rates(analysis)

        print(f"{self} Energy consumption:\n{self.energy.data}")
        print(f"\nCumulative emissions to Environment:\n{self.emissions.data}")
        print(f"Total: {self.ghgs} (UNITS?) CO2eq")

    def get_energy_rates(self, analysis):
        """
        Return the energy consumption rates by summing those of our children nodes,
        recursively working our way down the Container hierarchy, and storing each
        result at each container level.
        """
        self.energy.data[:] = 0.0
        data = self.energy.data

        for child in self.children():
            child_data = child.get_energy_rates(analysis)
            data += child_data

        return data

    def get_emission_rates(self, analysis):
        """
        Return a tuple of the emission rates (Series) and the calculated GHG value (float).
        Uses the current choice of GWP values in the enclosing Model.

        :return: ((pandas.Series, float)) a tuple containing the emissions Series
            and the GHG value computed using the model's current GWP settings.
        """
        # TBD: Are emissions in same units (e.g., kg CO2eq / day) or in terms of energy flow?
        self.emissions.data[:] = 0.0
        data = self.emissions.data
        ghgs = 0.0

        for child in self.children():
            child_data, child_ghgs = child.get_emission_rates(analysis)
            data += child_data
            ghgs += child_ghgs

        self.ghgs = ghgs
        return (data, ghgs)
