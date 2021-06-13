'''
.. Emissions handling

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''

import pandas as pd
import pint_pandas
from . import ureg
from .core import OpgeeObject, magnitude
from .error import OpgeeException
from .stream import Stream, PHASE_GAS
from .log import getLogger

_logger = getLogger(__name__)

EM_COMBUSTION = 'Combustion'
EM_LAND_USE   = 'Land-use'
EM_VENTING    = 'Venting'
EM_FLARING    = 'Flaring'
EM_FUGITIVES  = 'Fugitives'
EM_OTHER      = 'Other'

class EmissionsError(OpgeeException):
    def __init__(self, func_name, category, gas):
        self.func_name = func_name
        self.category = category
        self.gas = gas

    def __str__(self):
        if self.category not in Emissions._categories_set:
            return f"{self.func_name}: Unrecognized category '{self.category}'"

        if self.gas not in Emissions._emissions_set:
            return f"{self.func_name}: Unrecognized gas '{self.gas}'"


class Emissions(OpgeeObject):
    """
    Emissions is an object wrapper around a pandas.Series holding emission flow
    rates for a pre-defined set of substances, defined in ``Emissions.emissions``.
    """

    #: `Emissions.emissions` defines the set of substances tracked by this class.
    #: In addition, the `Model` class computes CO2-equivalent GHG emission using its
    #: current settings for GWP values and stored in the a row with index 'GHG'.
    emissions = ['VOC', 'CO', 'CH4', 'N2O', 'CO2']

    # for faster test for inclusion in this list
    _emissions_set = set(emissions)

    indices = emissions + ['GHG']

    categories = [EM_COMBUSTION, EM_LAND_USE, EM_VENTING, EM_FLARING, EM_FUGITIVES, EM_OTHER]
    _categories_set = set(categories)

    _units = ureg.Unit("tonne/day")

    @classmethod
    def create_emissions_matrix(cls):
        """
        Create a pandas DataFrame to hold emissions.

        :return: (pandas.DataFrame) Zero-filled emissions DataFrame
        """
        return pd.DataFrame(data=0.0, index=cls.indices, columns=cls.categories, dtype="pint[tonne/day]")

    def __init__(self):
        self.data = self.create_emissions_matrix()

    @classmethod
    def units(cls):
        return cls._units

    def reset(self):
        # Note: neither self.data[:] = 0.0 nor self.data.loc[:, :] = 0.0 work properly: these
        # reset the dtype to float, losing the pint units. The expression below works as we'd like.
        self.data.loc[self.data.index, :] = 0.0

    def rates(self, gwp=None):
        """
        Return the emission rates, and optionally, the calculated GHG value.

        :param gwp: (pandas.Series or None) the GWP values to use to compute GHG
        :return: (pandas.DataFrame) If `gwp` is none, the 'GHG' row of the DataFrame
            will contain zeroes, otherwise CO2-equivalents will be computed computed
            using the Series `gwp`.
        """
        if gwp is None:
            self.reset_GHG()
        else:
            self.compute_GHG(gwp)

        return self.data

    def compute_GHG(self, gwp):
        """
        Compute and store total CO2-eq GHGs using the given Series of GWP values.

        :param gwp: (pandas.Series) the GWP values to use, expected to have the
            same index as self.data (i.e., Emissions.emissions)
        :return: none
        """
        product = self.data.T[self.emissions] * gwp
        self.data.loc['GHG'] = product.sum(axis='columns')

    def reset_GHG(self):
        """
        Reset all GHG values to zeroes.

        :return: none
        """
        self.data.loc['GHG'] = 0.0

    def _check_loc(self, func_name, gas, category):
        if category not in self._categories_set or gas not in self._emissions_set:
            raise EmissionsError(f"Emissions.{func_name}", category, gas)

    def set_rate(self, category, gas, rate):
        """
        Set the rate of emissions for a single gas.

        :param category: (str) one of the defined emissions categories
        :param gas: (str) one of the defined emissions (values of Emissions.emissions)
        :param rate: (float) the rate in the Process' flow units (e.g., mmbtu (LHV) of fuel burned)
        :return: none
        """
        self._check_loc('set_rate', gas, category)
        self.data.loc[gas, category] = magnitude(rate, units=self._units)

    def set_rates(self, category, **kwargs):
        """
        Set the emissions rate for a single emissions category of one or more gases, given
        as keyword arguments, e.g., set_rates(CO2=100, CH4=30, N2O=6).

        :param category: (str) one of the defined emissions categories
        :param kwargs: (dict) the keyword arguments
        :return: none
        """
        for gas, rate in kwargs.items():
            self.set_rate(category, gas, rate)

    def add_rate(self, category, gas, rate):
        """
        Add to the stored rate of emissions for a single gas.

        :param category: (str) one of the defined emissions categories
        :param gas: (str) one of the defined emissions (values of Emissions.emissions)
        :param rate: (float) the increment in rate in the Process' flow units (e.g., mmbtu (LHV) of fuel burned)
        :return: none
        """
        self._check_loc('add_rate', gas, category)
        self.data.loc[gas, category] += rate

    def add_rates(self, category, **kwargs):
        """
        Add emissions to those already stored, for the given emissions `category`, of one
        or more gases, given as keyword arguments, e.g., add_rates('Venting', CO2=100, CH4=30, N2O=6).

        :param category: (str) one of the defined emissions categories
        :param kwargs: (dict) the keyword arguments
        :return: none
        """
        for gas, rate in kwargs.items():
            self.add_rate(category, gas, rate)

    def add_from_stream(self, category, stream):
        """
        Add emission flow rates from a Stream instance to the given emissions category.

        :param category: (str) one of the defined emissions categories
        :param stream: (Stream)
        :return: none
        """
        self.add_rate(category, 'CO2', stream.gas_flow_rate('CO2'))
        self.add_rate(category, 'CH4', stream.gas_flow_rate('C1'))

        # TBD: where to get CO and N2O?

        # All gas-phase hydrocarbons heavier than methane are considered VOCs
        VOCs = [f'C{n}' for n in range(2, Stream.max_carbon_number + 1)]  # skip C1 == CH4
        voc_rate = stream.components.loc[VOCs, PHASE_GAS].sum()
        self.add_rate(category, 'VOC', voc_rate)
