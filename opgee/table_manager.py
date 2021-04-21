# pkgutil doesn't provide a method to discover all the files in a package subdirectory
# so we identify the basenames of the files here and then extract them into a structure.
import os
import pandas as pd
from opgee.error import OpgeeException
from opgee.pkg_utils import resourceStream

class TableDef(object):
    """
    Holds definition of tables, allowing for optional arguments with defaults.
    """
    def __init__(self, basename, index_col=None, skiprows=0, units=None):
        self.basename = basename
        self.index_col = index_col
        self.skiprows = skiprows
        self.units = units

class TableManager(object):

    # List of tuples of CSV file basename and args to index_col keyword.
    # - First item is basename of table in the "tables" directory.
    # - Second item is passed to pandas.read_csv's index_col arg, so anything
    #   legal there is fine here, e.g., a single str or int, an iterable of str
    #   or int (for multi-column index), False (create simple integer index),
    #   or None (default; uses 1st col as index.)
    # - Third item is optional; if given, it's the number of rows to skip,
    #   allowing for comments.

    table_defs = [
        TableDef('constants', index_col='name'),
        TableDef('GWP', index_col=False),
        TableDef('bitumen-mining-energy-intensity', index_col=0),
        TableDef('transport-specific-EF', index_col=('Mode', 'Fuel'), skiprows=1, units='g/mmbtu'),
        TableDef('stationary-application-EF', index_col=('Fuel', 'Application'), skiprows=1, units='g/mmbtu'),
    ]

    def __init__(self):
        self.table_dict = table_dict = {}

        # TBD: load tables on demand
        for t in self.table_defs:
            relpath = f"tables/{t.basename}.csv"
            s = resourceStream(relpath, stream_type='text')
            df = pd.read_csv(s, index_col=t.index_col, skiprows=t.skiprows)
            table_dict[t.basename] = df

    def get_table(self, name):
        """
        Retrieve a dataframe representing CSV data loaded by the TableManager

        :param name: (str) the name of a table
        :return: (pandas.DataFrame) the corresponding data
        :raises: OpgeeException if the `name` is unknown.
        """
        try:
            return self.table_dict[name]
        except KeyError:
            raise OpgeeException(f"Failed to find table named {name}.")

    def add_table(self, pathname, index_col=None):
        """
        Add a CSV file external to OPGEE to the TableManager.

        :param pathname: (str) the pathname of a CSV file
        :param index_col: (str, int, iterable of str or int, False, or None) see doc for pandas.read_csv()
        :return: none
        """
        df = pd.read_csv(pathname, index_col=index_col)
        name = os.path.splitext(os.path.basename(pathname))[0]
        self.table_dict[name] = df
