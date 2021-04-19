# pkgutil doesn't provide a method to discover all the files in a package subdirectory
# so we identify the basenames of the files here and then extract them into a structure.
import os
import pandas as pd
from ..error import OpgeeException
from ..pkg_utils import resourceStream

class TableManager(object):

    # List of tuples of CSV file basename and args to index_col keyword.
    basenames = [('dummy', False)]

    def __init__(self):
        self.table_dict = table_dict = {}

        for (basename, index_col) in self.basenames:
            relpath = f"tables/{basename}.csv"
            s = resourceStream(relpath, stream_type='text')
            df = pd.read_csv(s, index_col=index_col)
            table_dict[basename] = df

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
        :param index_col: (str, int, False, or None) see doc for pandas.read_csv()
        :return: none
        """
        df = pd.read_csv(pathname, index_col=index_col)
        name = os.path.splitext(os.path.basename(pathname))[0]
        self.table_dict[name] = df
