# pkgutil doesn't provide a method to discover all the files in a package subdirectory
# so we identify the basenames of the files here and then extract them into a structure.
import os
import pandas as pd
from .core import OpgeeObject
from .error import OpgeeException
from .log import getLogger
from .pkg_utils import resourceStream

_logger = getLogger(__name__)


class TableDef(object):
    """
    Holds meta-data for built-in tables (CSV files loaded into `pandas.DataFrames`).
    """
    def __init__(self, basename, index_col=None, skiprows=0, units=None):
        self.basename = basename
        self.index_col = index_col
        self.skiprows = skiprows
        self.units = units

class TableManager(OpgeeObject):
    """
    The TableManager loads built-in CSV files into DataFrames and stores them in a dictionary keyed by the root name
    of the table. When adding CSV files to the opgee “tables” directory, a corresponding entry must be added in the
    TableManager class variable ``TableManager.table_defs``, which holds instances of `TableDef` class.

    Users can add external tables using the ``add_table`` method.
    """
    table_defs = [
        TableDef('constants', index_col='name'),
        TableDef('GWP', index_col=False),
        TableDef('bitumen-mining-energy-intensity', index_col=0),
        TableDef('transport-specific-EF', index_col=('Mode', 'Fuel'), skiprows=1, units='g/mmbtu'),
        TableDef('stationary-application-EF', index_col=('Fuel', 'Application'), skiprows=1, units='g/mmbtu'),
        TableDef('venting_fugitives_by_process', index_col=False, units='fraction'),
        TableDef("process-specific-EF.csv", index_col=("Process"), units="g/mmbtu")
        # TODO: see updates from OGPEE github
        # TableDef('separator_capacity', index_col=False, skiprows=1),
    ]

    _table_def_dict = {tbl_def.basename : tbl_def for tbl_def in table_defs}

    def __init__(self):
        self.table_dict = {}

    def get_table(self, name, raiseError=True):
        """
        Retrieve a dataframe representing CSV data loaded by the TableManager

        :param name: (str) the name of a table
        :param raiseError: (bool) whether to raise an error (or just return None) if the table isn't found.
        :return: (pandas.DataFrame) the corresponding data
        :raises: OpgeeException if the `name` is unknown and `raiseError` is True.
        """
        df = self.table_dict.get(name)

        # load on demand, if a TableDef is found
        if df is None:
            try:
                tbl_def = self._table_def_dict[name]
            except KeyError:
                if raiseError:
                    raise OpgeeException(f"Unknown table '{name}'")
                else:
                    return None

            relpath = f"tables/{name}.csv"
            s = resourceStream(relpath, stream_type='text')
            df = pd.read_csv(s, index_col=tbl_def.index_col, skiprows=tbl_def.skiprows)
            self.table_dict[name] = df

        return df

    def add_table(self, pathname, index_col=None, skiprows=0): #  , units=None):
        """
        Add a CSV file external to OPGEE to the TableManager.

        :param pathname: (str) the pathname of a CSV file
        :param index_col: (str, int, iterable of str or int, False, or None) see doc
            for `pandas.read_csv()`
        :param skiprows: (int) the number of rows to skip before the table begins.
        :return: none
        """
        df = pd.read_csv(pathname, index_col=index_col, skiprows=skiprows)
        name = os.path.splitext(os.path.basename(pathname))[0]
        self.table_dict[name] = df
