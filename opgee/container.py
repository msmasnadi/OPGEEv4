'''
.. OPGEE Container and Aggregator classes

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''
from .core import XmlInstantiable
from .emissions import Emissions
from .energy import Energy
from .error import OpgeeException
from .log import getLogger

_logger = getLogger(__name__)

class Container(XmlInstantiable):
    """
    Generic hierarchical node element, has a name and contains other Containers and/or
    Processes (and subclasses thereof).
    """
    def __init__(self, name, attr_dict=None, aggs=None, procs=None):
        super().__init__(name)

        self.emissions = Emissions()
        self.energy = Energy()
        self.ghgs = 0.0

        self.attr_dict = attr_dict or {}
        self.aggs  = self.adopt(aggs)
        self.procs = self.adopt(procs)

    def attr(self, attr_name, default=None, raiseError=False):
        obj = self.attr_dict.get(attr_name)
        if obj is None and raiseError:
            raise OpgeeException(f"Attribute '{attr_name}' not found in {self}")

        return obj.value or default

    def run(self, names=None, **kwargs):
        """
        Run all children of this Container if `names` is None, otherwise run only the
        children whose names are in in `names`.

        :param names: (None, or list of str) the names of children to run
        :param kwargs: (dict) arbitrary keyword args to pass through
        :return: None
        """
        if self.is_enabled():
            self.print_running_msg()
            self.run_children(names=names, **kwargs)

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

    def run_children(self, names=None, **kwargs):
        for child in self.children():
            if names is None or child.name in names:
                child.run(**kwargs)

        # TBD: else self.bypass()?

    def get_energy_rates(self):
        """
        Return the energy consumption rates by summing those of our children nodes,
        recursively working our way down the Container hierarchy.
        """
        self.energy.data[:] = 0.0
        data = self.energy.data

        for child in self.children():
            child_data = child.get_energy_rates()
            data += child_data

        return data

    def get_emission_rates(self):
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
            child_data, child_ghgs = child.get_emission_rates()
            data += child_data
            ghgs += child_ghgs

        self.ghgs = ghgs
        return (data, ghgs)
