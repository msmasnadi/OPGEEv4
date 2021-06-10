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


class Emissions(OpgeeObject):
    """
    Emissions is an object wrapper around a pandas.Series holding emission flow
    rates for a pre-defined set of substances, defined in ``Emissions.emissions``.
    """

    #: `Emissions.emissions` defines the set of substances tracked by this class.
    #: In addition, the `Model` class computes CO2-equivalent GHG emission using its
    #: current settings for GWP values. The GHG value is cached in the `Emissions`
    #: instance.
    emissions = ['VOC', 'CO', 'CH4', 'N2O', 'CO2']

    # for faster test for inclusion in this list
    _emissions_set = set(emissions)

    _units = ureg.Unit("tonne/day")

    @classmethod
    def create_emissions_series(cls):
        """
        Create a pandas Series to hold emissions.

        :return: (pandas.Series) Zero-filled emissions Series
        """
        return pd.Series(data=0.0, index=cls.emissions, name='emissions', dtype="pint[tonne/day]")

    def __init__(self):
        self.data = self.create_emissions_series()
        self.ghg = ureg.Quantity(0.0, self.units())

    @classmethod
    def units(cls):
        return cls._units

    def rates(self, gwp=None):
        """
        Return the emission rates, and optionally, the calculated GHG value.

        :param gwp: (pandas.Series or None) the GWP values to use to compute GHG
        :return: (pandas.Series or tuple of (pandas.Series, float) if `gwp` is none,
            the Series of emission rates is returned. Otherwise, a tuple is returned
            containing the Series and the GHG value computed using `gwp`.
        """
        return self.data if gwp is None else (self.data, self.GHG(gwp))

    def GHG(self, gwp):
        """
        Compute and cache total CO2-eq GHGs using the given Series of GWP values.

        :param gwp: (pandas.Series) the GWP values to use, expected to have the
            same index as self.data (i.e., Emissions.emissions)
        :return: (float) the sum of GWP-weighted emissions
        """
        self.ghg = sum(gwp * self.data)  # TBD: store this? Could create inconsistencies...
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

        self.data[gas] = magnitude(rate, units=self._units)

    def set_rates(self, **kwargs):
        """
        Set the emissions rate of one or more gases, given as keyword arguments, e.g.,
        set_rates(CO2=100, CH4=30, N2O=6).

        :param kwargs: (dict) the keyword arguments
        :return: none
        """
        for gas, rate in kwargs.items():
            self.set_rate(gas, rate)

    def add_rate(self, gas, rate):
        """
        Add to the stored rate of emissions for a single gas.

        :param gas: (str) one of the defined emissions (values of Emissions.emissions)
        :param rate: (float) the increment in rate in the Process' flow units (e.g., mmbtu (LHV) of fuel burned)
        :return: none
        """
        if gas not in self._emissions_set:
            raise OpgeeException(f"Emissions.add_rate: Unrecognized gas '{gas}'")

        self.data[gas] += rate

    def add_rates(self, **kwargs):
        """
        Add emissions to those already stored, for of one or more gases, given as
        keyword arguments, e.g., add_rates(CO2=100, CH4=30, N2O=6).

        :param kwargs: (dict) the keyword arguments
        :return: none
        """
        for gas, rate in kwargs.items():
            self.add_rate(gas, rate)

    def add_from_stream(self, stream):
        """
        Add emission flow rates from a Stream instance.

        :param stream: (Stream)
        :return: none
        """
        self.add_rate('CO2', stream.gas_flow_rate('CO2'))
        self.add_rate('CH4', stream.gas_flow_rate('C1'))

        # TBD: where to get CO and N2O?

        # Any gas-phase hydrocarbon heavier than methane is considered a VOC
        VOCs = [f'C{n}' for n in range(2, Stream.max_carbon_number + 1)]  # skip C1 == CH4
        voc_rate = stream.components.loc[VOCs, PHASE_GAS].sum()
        self.add_rate('VOC', voc_rate)
