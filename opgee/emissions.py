'''
.. Emissions handling

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
'''

import pandas as pd
from .core import OpgeeObject
from .error import OpgeeException

class Emissions(OpgeeObject):

    # GHG is the CO2-eq computed using user's choice of GWP values
    # Note that Model uses this to set order of GWP values.
    emissions = ['VOC', 'CO', 'CH4', 'N2O', 'CO2']

    # for faster test for inclusion in this list
    _emissions_set = set(emissions)

    @classmethod
    def create_emissions_series(cls, unit=None):
        """
        Create a pandas Series to hold emissions.

        :param unit: (str or pint units) the units assigned to these emissions
        :return: (pandas.Series) Zero-filled emissions Series
        """
        # TBD: use the units via pint's pandas support
        return pd.Series(data=0.0, index=cls.emissions, name='emissions', dtype=float)

    def __init__(self, unit=None):
        self.data = self.create_emissions_series(unit=unit)
        self.unit = unit
        self.ghg = 0.0

    def GHG(self, gwp):
        """
        Compute GHG using the given Series of GWP values.

        :param gwp: (pandas.Series) the GWP values to use, expected to have the
            same index as self.data (i.e., Emissions.emissions)
        :return: (float) the sum of GWP-weighted emissions
        """
        self.ghg = sum(gwp * self.data)
        return self.ghg

    def set_rate(self, gas, rate):
        """
        Set the rate of emissions for a single gas.

        :param gas: (str) one of the defined emissions (values of Emissions.emissions)
        :param rate: (float) the rate in the Process' flow units (e.g., mmbtu (LHV) of fuel burned)
        :return: none
        """
        if gas not in self._emissions_set:
            raise OpgeeException(f"Emissions.set_rate: Unrecognized gas '{gas}'")

        self.data[gas] = rate

    def set_rates(self, **kwargs):
        """
        Set the emissions rate of one or more gases, given as keyword arguments, e.g.,
        set_rate(CO2=100, CH4=30, N2O=6).

        :param kwargs: (dict) the keyword arguments
        :return: none
        """
        data = self.data
        for gas, rate in kwargs.items():

            if gas not in self._emissions_set:
                raise OpgeeException(f"Emissions.set_rates: Unrecognized gas '{gas}'")

            data[gas] = rate
