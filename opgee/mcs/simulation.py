#
# Simulation class
#
# Author: Richard Plevin
#
# Copyright (c) 2022 the author and The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import os
from ..config import getParam, pathjoin
from ..core import OpgeeObject
from ..error import McsSystemError
from ..utils import mkdirs

# TBD: maybe have a "results" subdir, with file f"{analysis.name}.csv" for results of 1 analysis?

class Simulation(OpgeeObject):
    """
    ``Simulation`` represents the file and directory structure of a Monte Carlo simulation.
    Each simulation has an associated top-level directory which contains:

    - `trial_data.csv`: values drawn from parameter distributions, with each row representing
      a single trial, and each column representing the vector of values drawn for a single
      parameter. This file is created by the "gensim" sub-command.

    - `analysis_XXX.csv`: results for the analysis named `XXX`. Each column represents the
      results of a single output variable. Each row represents the value of all output variables
      for one trial of a single field. The field name is thus included in each row, allowing
      results for all fields in a single analysis to be stored in one file.

    - `trials`: a directory holding subdirectories for each trial, allowing each to be run
      independently (e.g., on a multi-core or cluster computer). The directory structure under
      ``trials`` comprises two levels of 3-digit values, which, when concatenated form the
      trial number. That is, trial 1,423 would be found in ``trials/001/423``. This allows
      up to 1 million trials while ensuring that no directory contains more than 1000 items.
      Limiting directory size improves performance.
    """
    def __init__(self, pathname):
        self.pathname = pathname
        self.trial_data_path = None
        self.trial_data_df = None # loaded on demand by ``trial_data`` method.
        pass

    @classmethod
    def new(cls, pathname):
        """
        Create the simulation directory and the ``sandboxes`` sub-directory.

        :param pathname: (str) the top-level pathname
        :return: a new ``Simulation`` instance
        """
        pass

    def trial_dir(self, trial_num, mkdir=False):
        """
        Return the full pathname to the data for trial ``trial_num``,
        optionally creating the directory.

        :param trial_num: (int) the trial number
        :param mkdir: (bool) whether to make the directory, if needed
        :return: the trial's data directory
        """
        upper = trial_num // 1000
        lower = trial_num % 1000
        trial_dir = pathjoin(self.pathname, 'trials', f"{upper:03d}", f"{lower:03d}")

        if mkdir:
            mkdirs(trial_dir)

        return trial_dir

    def consolidate_results(self):
        """
        Walk the trial directories, accumulating results into a single top-level
        results file.

        :return: the pathname of the results file.
        """
        pass

    def trial_data(self):
        """
        Read trial_data.csv from the top-level directory and return the DataFrame.
        The data is cached in the ``Simulation`` instance for re-use.

        :return: (pd.DataFrame) the values drawn for each field, parameter, and trial.
        """
        import pandas as pd

        # TBD: allow option of using same draws across fields.
        if self.trial_data_df:
            return self.trial_data_df

        path = pathjoin(self.pathname, 'trial_data.csv')
        if not os.path.lexists(path):
            raise McsSystemError(f"Can't read trial data: '{path}' doesn't exist.")

        try:
            df = pd.read_csv(path, index_col='trial_num')

        except Exception as e:
            raise McsSystemError(f"Can't read trial data from '{path}': {e}")

        self.trial_data_path = path
        self.trial_data_df = df
        return df

    def trial_values(self, trial_num):
        """
        Return the values for all parameters for trial ``trial_num``.

        :param trial_num: (int) trial number
        :return: (pd.Series) the values for all parameters for the given trial.
        """
        df = self.trial_data()  # load data file on demand

        if trial_num not in df.index:
            raise McsSystemError(f"Trial {trial_num} was not found in '{self.trial_data_path}'")

        s = df[trial_num]
        return s

    def save_trial_data(self):
        # TBD: just write the file or also perform all the draws from distros?
        pass

