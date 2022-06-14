#
# Simulation class
#
# Author: Richard Plevin
#
# Copyright (c) 2022 the author and The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import os
from ..config import pathjoin
from ..core import OpgeeObject
from ..error import McsSystemError, McsUserError
from ..log import getLogger
from ..pkg_utils import resourceStream
from ..smart_defaults import Dependency
from ..utils import mkdirs, removeTree
from .LHS import lhs
from .distro import get_frozen_rv

_logger = getLogger(__name__)

TRIAL_DATA_CSV = 'trial_data.csv'
RESULTS_DIR = 'results'
MODEL_FILE = 'merged_model.xml'

DISTROS_CSV = 'mcs/etc/parameter_distributions.csv'

def read_distributions(pathname=None):
    """
    Read distributions from the designated CSV file. These are combined with those defined
    using the @Distribution.register() decorator, used to define distributions with dependencies.

    :param pathname: (str) the pathname of the CSV file describing parameter distributions
    :return: (none)
    """
    import pandas as pd

    distros_csv = pathname or resourceStream(DISTROS_CSV, stream_type='bytes', decode=None)

    df = pd.read_csv(distros_csv, skip_blank_lines=True, comment='#').fillna('')

    for row in df.itertuples(index=False, name='row'):
        shape = row.distribution_type.lower()
        name = row.variable_name
        low = row.low_bound
        high = row.high_bound
        mean = row.mean
        stdev = row.SD
        default = row.default_value
        prob_of_yes = row.prob_of_yes

        if low == '' and high == '' and mean == '' and prob_of_yes == '':
            _logger.info(f"* {name} depends on other distributions / smart defaults")        # TODO add in lookup of attribute value
            continue

        if shape == 'binary':
            if prob_of_yes == 0 or prob_of_yes == 1:
                _logger.info(f"* Ignoring distribution on {name}, Binary distribution has prob_of_yes = {prob_of_yes}")
                continue

            rv = get_frozen_rv('weighted_binary', prob_of_one=0.5 if prob_of_yes == '' else prob_of_yes)

        elif shape == 'uniform':
            if low == high:
                _logger.info(f"* Ignoring distribution on {name}, Uniform high and low bounds are both {low}")
                continue

            rv = get_frozen_rv('uniform', min=low, max=high)

        elif shape == 'triangular':
            if low == high:
                _logger.info(f"* Ignoring distribution on {name}, Triangle high and low bounds are both {low}")
                continue

            rv = get_frozen_rv('triangle', min=low, mode=default, max=high)

        elif shape == 'normal':
            if stdev == 0.0:
                _logger.info(f"* Ignoring distribution on {name}, Normal has stdev = 0")
                continue

            if low == '' or high == '':
                rv = get_frozen_rv('normal', mean=mean, stdev=stdev)
            else:
                rv = get_frozen_rv('truncated_normal', mean=mean, stdev=stdev, low=low, high=high)

        elif shape == 'lognormal':
            if stdev == 0.0:
                _logger.info(f"* Ignoring distribution on {name}, Lognormal has stdev = 0")
                continue

            rv = get_frozen_rv('lognormal', logmean=mean, logstdev=stdev)

        else:
            raise McsSystemError(f"Unknown distribution shape: '{shape}'")

        # merge CSV-based distros with decorator-based ones
        Distribution.register_rv(rv, name)


class Distribution(Dependency):
    def __init__(self, rv, attr_name):
        func_name = ''   # unused in Distribution
        func_class = ''  # unused in Distribution
        deps = []        # unused in Distribution
        super().__init__(func_class, func_name, rv, attr_name, deps)

    @classmethod
    def distributions(cls):
        """
        Return a list of the defined Distribution instances.

        :return: (list of opgee.mcs.Distribution) the instances
        """
        rows = cls.registry.query("dep_type == 'Distribution'")

        dep_objs = list(rows.dep_obj.values)
        return dep_objs

    @classmethod
    def register_rv(cls, rv, attr_name):
        Distribution(rv, attr_name)

    def __str__(self):
        deps = f" {self.dependencies}" if self.dependencies else ''

        return f"<Distribution '{self.attr_name}'={self.func}{deps}>"

# TBD: maybe have a "results" subdir, with file  for results of 1 analysis?

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

        self.trial_data_path = pathjoin(pathname, TRIAL_DATA_CSV)
        self.trial_data_df = None # loaded on demand by ``trial_data`` method.

        self.analysis_name = None

        self.results_dir = pathjoin(pathname, RESULTS_DIR)      # stores f"{analysis.name}.csv"
        # self.results_file = None

        self.model_file = pathjoin(pathname, MODEL_FILE)

    @classmethod
    def new(cls, pathname, overwrite=False):
        """
        Create the simulation directory and the ``sandboxes`` sub-directory.

        :param pathname: (str) the top-level pathname
        :param overwrite: (bool) if True, overwrite directory if it already exists,
          otherwise refuse to do so.
        :return: a new ``Simulation`` instance
        """
        if os.path.lexists(pathname):
            if not overwrite:
                raise McsUserError(
                    f"Directory '{pathname}' already exists. Use Simulation.new(pathname, overwrite=True) to replace it.")

            removeTree(pathname, ignore_errors=False)

        mkdirs(pathname)

        sim = cls(pathname)
        return sim

    # TBD: need a way to specify correlations
    def generate(self, analysis, N, corr_mat=None):
        """
        Generate simulation data for the given ``Analysis`` object.

        :param analysis: (opgee.Analysis) the analysis to generate MCS for
        :param N: (int) the number of trials to generate data for
        :param corr_mat: a numpy matrix representing the correlation
           between each pair of parameters. corrMat[i,j] gives the
           desired correlation between the i'th and j'th entries of
           the parameter list.
        :return: none
        """
        # TBD: could create copy of Analysis.attr_dict, then for each Field,
        #  merge its attr_dict onto the Analysis one to create one lookup table?
        #  Nah, it's more efficient just to do lookup in Field, then fallback to
        #  Analysis, since almost all are in Field. No copying required.
        self.analysis_name = analysis.name
        attr_dict = analysis.attr_dict

        # TODO: revise to use rv_dict rather than @Distribution decorator
        cols = []
        rv_list = []

        by_attr = Distribution.registry.set_index('attr_name')

        # TBD: registry has multiple entries for some attributes -- both SmartDefault and Distribution
        #   For MCS, use distribution if it exists, otherwise the SmartDefault -- but not both.
        #   Better to have separate dicts for these rather than merged into one table?
        #   - SmartDefaults (in non-mcs mode) run order requires only smart defaults
        #   - Distribution run order may depend on SmartDefaults, but need to look for dependent Distribution first
        #   Processing will require stepping through each trial value

        for dep_obj in Distribution.distributions():
            args = [attr_dict[attr_name] for attr_name in dep_obj.dependencies if attr_name != '_']
            if args:
                print(f"{dep_obj.attr_name}: calling {dep_obj.func}({args})")
                rv = dep_obj.func(*args)
            else:
                rv = dep_obj.func

            rv_list.append(rv)
            cols.append(dep_obj.attr_name)

        self.trial_data_df = df = lhs(rv_list, N, columns=cols, corrMat=corr_mat)
        df.index.name = 'trial_num'
        self.save_trial_data()

    def save_trial_data(self):
        self.trial_data_df.to_csv(self.trial_data_path)


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
        Read the trial data CSV from the top-level directory and return the DataFrame.
        The data is cached in the ``Simulation`` instance for re-use.

        :return: (pd.DataFrame) the values drawn for each field, parameter, and trial.
        """
        import pandas as pd

        # TBD: allow option of using same draws across fields.
        if self.trial_data_df:
            return self.trial_data_df

        path = self.trial_data_path
        if not os.path.lexists(path):
            raise McsSystemError(f"Can't read trial data: '{path}' doesn't exist.")

        try:
            df = pd.read_csv(path, index_col='trial_num')

        except Exception as e:
            raise McsSystemError(f"Can't read trial data from '{path}': {e}")

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
