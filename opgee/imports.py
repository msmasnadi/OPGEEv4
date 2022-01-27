import pandas as pd
import pint
from .core import OpgeeObject
from .error import OpgeeException

from .log import getLogger

_logger = getLogger(__name__)


class Imports(OpgeeObject):
    NATURAL_GAS = "NG"
    UPG_PROC_GAS = "upg_proc_gas"
    NGL_LPG = "NLG_LPG"
    DILUENT = "diluent"
    CRUDE_OIL = "crude_oil"  # (does not contain diluent if any)
    DIESEL = "diesel"
    RESID = "resid"
    PETCOKE = "petcoke"
    ELECTRICITY = "electricity"
    WATER = "water"

    unit_dict = {NATURAL_GAS : "mmbtu/day",
                 UPG_PROC_GAS: "mmbtu/day",
                 NGL_LPG     : "mmbtu/day",
                 DILUENT     : "mmbtu/day",
                 CRUDE_OIL   : "mmbtu/day",
                 DIESEL      : "mmbtu/day",
                 RESID       : "mmbtu/day",
                 PETCOKE     : "mmbtu/day",
                 ELECTRICITY : "mmbtu/day",
                 WATER       : "gal/day"}

    imports_set = set(unit_dict.keys())

    @classmethod
    def create_import_df(cls):
        """
         Create a DataFrame to hold import rates.

         :return: (pandas.DataFrame) An empty imports DataFrame with
            the columns and types set
         """
        df = pd.DataFrame({name : pd.Series([], dtype=f"pint[{units}]")
                           for name, units in cls.unit_dict.items()})

        return df

    def __init__(self):
        self.df = self.create_import_df()

    def add_import(self, proc_name, item, value):
        """
        Add imports for a given ``item`` by process ``proc_name``, of
        quantity ``value``.

        :param proc_name: (str) the name of a process
        :param item: (str) one of the known import items (see Imports.imports_set)
        :param value: (float or pint.Quantity) the quantity imported. If a Quantity
           is passed, it is converted to the import's standard units.
        :return: none
        """
        if item not in self.imports_set:
            raise OpgeeException(f"Tried to add import of unknown item '{item}'")

        df = self.df

        if proc_name not in df.index:
            df.loc[proc_name, :] = 0.0

        if isinstance(value, pint.Quantity):
            value = value.to(df[item].pint.units).m  # get value in expected units

        self.df.loc[proc_name, item] = value

    def importing_processes(self):
        """
        Return a list of the names of importing processes.
        """
        return list(self.df.index)

    def total_imports(self):
        """
        Return a dictionary keyed by import category with the total
        net imports for that category.

        :return: (list of pint.Quantity) total net imports by category
        """
        df = self.df
        totals = {name : df[name].sum() for name in df.columns}
        return pd.Series(totals)

    def proc_imports(self, proc_name):
        """
        Return a Series holding the imports for the given ``proc_name``.

        :param proc_name: (str) the name of a process
        :return: (pandas.Series) the values stored for the ``proc_name``
        """
        row = self.df.loc[proc_name]
        return row
