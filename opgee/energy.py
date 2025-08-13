#
# Energy use tracking
#
# Author: Richard Plevin
#
# Copyright (c) 2021-2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import pandas as pd

from .units import ureg
from .core import OpgeeObject
from .error import OpgeeException
from .log import getLogger

_logger = getLogger(__name__)

# TBD: Decide if these strings are the ones we want to use throughout. Some seem a bit random.
EN_NATURAL_GAS = 'Natural gas'
EN_UPG_PROC_GAS = 'Upgrader proc. gas'
EN_NGL = 'NGL'
EN_CRUDE_OIL = 'Crude oil'
EN_DIESEL = 'Diesel'
EN_RESID = 'Residual fuel'
EN_PETCOKE = 'Pet. coke'
EN_ELECTRICITY = 'Electricity'


class Energy(OpgeeObject):
    """
    Energy is an object wrapper around a pandas.Series holding energy consumption
    rates for a pre-defined set of energy carriers, defined in ``Energy.carriers``.
    """

    #: `carriers` defines the energy carriers tracked by this class.
    #: Note that when used in the code, the defined variables (EN_NATURAL_GAS,
    #: EN_UPG_PROC_GAS, EN_NGL, EN_CRUDE_OIL, EN_DIESEL, EN_RESID, EN_PETCOKE,
    #: EN_ELECTRICITY) should be used to avoid dependencies on the specific strings.
    carriers = [EN_NATURAL_GAS, EN_UPG_PROC_GAS, EN_NGL, EN_CRUDE_OIL,
                EN_DIESEL, EN_RESID, EN_PETCOKE, EN_ELECTRICITY]

    _carrier_set = set(carriers)

    _units = ureg.Unit("mmbtu/day")

    @classmethod
    def create_energy_series(cls):
        """
         Create a pandas Series to hold energy consumption rates.

         :return: (pandas.Series) Zero-filled energy carrier Series
         """
        return pd.Series(data=0.0, index=cls.carriers, name='energy', dtype=f"pint[{cls._units}]")

    @classmethod
    def create_energy_process_series(cls):
        """
        Create a pandas DataFrame to hold process-level energy consumption.

        :return: (pandas.DataFrame) Zero-filled process-level energy DataFrame
        """
        # TODO SZ: check if this is correct with Rich
        # Create empty DataFrame
        df = pd.DataFrame(columns=['process', 'energy', 'value', 'unit'])

        # Force dtype for 'value' column
        df = df.astype({'value': f'pint[{cls._units}]'})

        return df

    def __init__(self):
        self.data = self.create_energy_series()
        self.process_data = self.create_energy_process_series()

    @classmethod
    def units(cls):
        return cls._units

    def rates(self):
        """
        Return the energy use data.

        :return: (pandas.Series) energy use data.
        """
        return self.data

    def get_rate(self, carrier):
        """
        Get the rate of energy use for a single carrier

        :param carrier: (str) one of the defined energy carriers (values of Energy.carriers)
        :return: (float) the rate of use for all energy sources in mmbtu/day (LHV), except
            for electricity, which is in mmbtu/day without LHV (no combustion to thermal
            energy), assuming 100% mechanical to thermal energy conversion.
        """
        if carrier not in self._carrier_set:
            raise OpgeeException(f"Energy.set_rate: Unrecognized carrier '{carrier}'")

        return self.data[carrier]

    def set_rate(self, carrier, rate):
        """
        Set the rate of energy use for a single carrier.

        :param carrier: (str) one of the defined energy carriers (values of Energy.carriers)
        :param rate: (float) the rate of use for all energy sources in mmbtu/day (LHV), except
            for electricity, which is in mmbtu/day without LHV (no combustion to thermal
            energy), assuming 100% mechanical to thermal energy conversion.
        :return: none
        """
        if carrier not in self._carrier_set:
            raise OpgeeException(f"Energy.set_rate: Unrecognized carrier '{carrier}'")

        self.data[carrier] = rate

    def set_rates(self, dictionary):
        """
        Set the energy use rate of one or more carriers.

        :param dictionary: (dict) the carriers and rates
        :return: none
        """
        for carrier, rate in dictionary.items():
            self.set_rate(carrier, rate)

    def set_process_rate(self, process_name, carrier, rate):
        if carrier not in self._carrier_set:
            raise OpgeeException(f"Energy.set_rate: Unrecognized carrier '{carrier}'")

        # Convert to class units before inserting
        rate = rate.to(self._units)  # ensures consistent unit

        self.process_data.loc[len(self.process_data)] = [
            process_name,
            carrier,
            rate,
            str(rate.units)  # store unit as string for human readability
        ]

    def add_rate(self, carrier, rate):
        """
        Add to the rate of energy use for a single carrier.

        :param carrier: (str) one of the defined energy carriers (values of Energy.carriers)
        :param rate: (float) the increment  rate of use for all energy sources in mmbtu/day (LHV),
            except for electricity, which is in mmbtu/day without LHV (no combustion to thermal
            energy), assuming 100% mechanical to thermal energy conversion.
        :return: none
        """
        if carrier not in self._carrier_set:
            raise OpgeeException(f"Energy.set_rate: Unrecognized carrier '{carrier}'")

        self.data[carrier] += rate

    def add_process_rate(self, process_name, carrier, rate):
        if carrier not in self._carrier_set:
            raise OpgeeException(f"Energy.set_rate: Unrecognized carrier '{carrier}'")

        # Convert to consistent units
        rate = rate.to(self._units)

        # Find matching row(s) in process_data
        mask = (
                (self.process_data['process'] == process_name) &
                (self.process_data['energy'] == carrier)
        )

        if mask.any():
            # Increment the rate in place
            self.process_data.loc[mask, 'value'] += rate
        else:
            # If not found, append a new row
            self.process_data.loc[len(self.process_data)] = [
                process_name,
                carrier,
                rate,
                str(rate.units)
            ]

    def add_rates(self, dictionary):
        """
        Add to the energy use rate for one or more carriers.

        :param dictionary: (dict) the carriers and rates
        :return: none
        """
        for carrier, rate in dictionary.items():
            self.add_rate(carrier, rate)

    def add_rates_from(self, energy):
        """
        Add rates from energy instance

        :param energy:
        :return:
        """
        self.data += energy.data

    def reset(self):
        """
        Reset energy instance

        :return:
        """
        self.data[self.data.index] = 0.0
