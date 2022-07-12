#
# Simulation class
#
# Author: Richard Plevin
#
# Copyright (c) 2022 the author and The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import json
import os
import pandas as pd

from ..config import pathjoin
from ..core import OpgeeObject
from ..error import McsSystemError, McsUserError, CommandlineError, ModelValidationError
from ..log import getLogger
from ..model_file import ModelFile
from ..pkg_utils import resourceStream
from ..utils import mkdirs, removeTree
from .LHS import lhs
from .distro import get_frozen_rv

_logger = getLogger(__name__)


TRIAL_DATA_CSV = 'trial_data.csv'
RESULTS_DIR = 'results'
MODEL_FILE = 'merged_model.xml'
META_DATA_FILE = 'metadata.json'

CLASS_DELIMITER = '.'

DISTROS_CSV = 'mcs/etc/parameter_distributions.csv'

def model_file_path(sim_dir):
    model_file = pathjoin(sim_dir, MODEL_FILE)
    return model_file

def read_distributions(pathname=None):
    """
    Read distributions from the designated CSV file. These are combined with those defined
    using the @Distribution.register() decorator, used to define distributions with dependencies.

    :param pathname: (str) the pathname of the CSV file describing parameter distributions
    :return: (none)
    """
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
        pathname = row.pathname

        if name == '':
            continue

        if low == '' and high == '' and mean == '' and prob_of_yes == '' and shape != 'empirical':
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

        elif shape == 'empirical':
            rv = get_frozen_rv('empirical', pathname=pathname, colname=name)

        else:
            raise McsSystemError(f"Unknown distribution shape: '{shape}'")

        # merge CSV-based distros with decorator-based ones
        Distribution(name, rv)


def split_attr_name(attr_name):
    splits = attr_name.split(CLASS_DELIMITER)
    count = len(splits)
    if count == 1:
        class_name, attr_name = 'Field', splits[0]
    elif count == 2:
        class_name, attr_name = splits
    else:
        raise McsUserError(f"read_distributions: attribute name format is 'ATTR' (same as 'Field.ATTR) or 'CLASS.ATTR'; got '{attr_name}'")

    return class_name, attr_name


class Distribution(OpgeeObject):

    instances = {}

    def __init__(self, full_name, rv):
        self.full_name = full_name
        self.class_name, self.attr_name = split_attr_name(full_name)
        self.rv = rv
        self.instances[full_name] = self

    @classmethod
    def distributions(cls):
        """
        Return a list of the defined Distribution instances.

        :return: (list of opgee.mcs.Distribution) the instances
        """
        return cls.instances.values()

    def __str__(self):
        return f"<Distribution '{self.full_name}' = {self.rv}>"


# TBD: maybe have a "results" subdir, with file  for results of 1 analysis?

class Simulation(OpgeeObject):
    """
    ``Simulation`` represents the file and directory structure of a Monte Carlo simulation.
    Each simulation has an associated top-level directory which contains:

    - `metadata.json`: currently, only the analysis name is stored here, but more stuff later.

    - `{field_name}/trial_data.csv`: values drawn from parameter distributions, with each row
      representing a single trial, and each column representing the vector of values drawn for
      a single parameter. This file is created by the "gensim" sub-command.

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
    def __init__(self, sim_dir, analysis_name=None, trials=0, field_names=None):
        self.pathname = sim_dir
        self.results_dir = pathjoin(sim_dir, RESULTS_DIR)
        self.model_file = model_file_path(sim_dir)

        # TBD: to allow the same trial_num to be run across fields, cache field
        #      trial_data in a dict by field name rather than a single DF

        self.trial_data_df = None # loaded on demand by ``trial_data`` method.
        self.trials = trials

        self.analysis_name = analysis_name
        self.analysis = None
        self.field_names = field_names
        self.metadata = None

        if analysis_name:
            self._save_meta_data()
        else:
            self._load_meta_data()

        if not os.path.isdir(self.pathname):
            raise McsUserError(f"Simulation directory '{self.pathname}' does not exist.")

        mf = ModelFile(self.model_file, use_default_model=False)
        self.model = mf.model

        self.analysis = analysis = self.model.get_analysis(self.analysis_name, raiseError=False)
        if not analysis:
            raise CommandlineError(f"Analysis '{self.analysis_name}' was not found in model")

        if trials > 0:
            self.generate()

    def _save_meta_data(self):
        self.metadata = {
            'analysis_name': self.analysis_name,
            'trials'       : self.trials,
            'field_names'  : self.field_names,  # None => process all Fields in the Analysis
        }

        with open(self.metadata_path(), 'w') as fp:
            json.dump(self.metadata, fp, indent=2)

    def _load_meta_data(self):
        with open(self.metadata_path(), 'r') as fp:
            self.metadata = metadata = json.load(fp)

        self.analysis_name = metadata['analysis_name']
        self.trials        = metadata['trials']
        self.field_names   = metadata['field_names']

    @classmethod
    def new(cls, sim_dir, model_files, analysis_name, trials,
            field_names=None, overwrite=False, use_default_model=True):
        """
        Create the simulation directory and the ``sandboxes`` sub-directory.

        :param sim_dir: (str) the top-level simulation directory
        :param model_files: (list of XML filenames) the XML files to load, in order to be merged
        :param analysis_name: (str) the name of the analysis for which to generate the MCS
        :param trials: (int) the number of trials to generate
        :param field_names: (list of str or None) Field names to limit the Simulation to use.
           (None => use all Fields defined in the Analysis.)
        :param overwrite: (bool) if True, overwrite directory if it already exists,
          otherwise refuse to do so.
        :param use_default_model: (bool) whether to use the default model in etc/opgee.xml as
           the baseline model to merge with.
        :return: a new ``Simulation`` instance
        """
        if os.path.lexists(sim_dir):
            if not overwrite:
                raise McsUserError(f"Directory '{sim_dir}' already exists. Use "
                                    "Simulation.new(sim_dir, overwrite=True) to replace it.")
            removeTree(sim_dir, ignore_errors=False)

        mkdirs(sim_dir)

        # Stores the merged model in the simulation folder to ensure the same one
        # is used for all trials. Avoids having each worker regenerate this, and
        # thus avoids different models being used if underlying files change while
        # the simulation is running.
        merged_model_file = model_file_path(sim_dir)
        mf = ModelFile(model_files, use_default_model=use_default_model, save_to_path=merged_model_file)

        analysis = mf.model.get_analysis(analysis_name, raiseError=False)
        if not analysis:
            raise McsUserError(f"Analysis '{analysis_name}' was not found in model")

        sim = cls(sim_dir, analysis_name=analysis_name, trials=trials, field_names=field_names)
        return sim

    def field_dir(self, field):
        d = pathjoin(self.pathname, field.name)
        return d

    def trial_data_path(self, field, mkdir=False):
        d = self.field_dir(field)
        if mkdir:
            mkdirs(d)
        path = pathjoin(d, TRIAL_DATA_CSV)
        return path

    def trial_dir(self, field, trial_num, mkdir=False):
        """
        Return the full pathname to the data for trial ``trial_num``,
        optionally creating the directory.

        :param trial_num: (int) the trial number
        :param mkdir: (bool) whether to make the directory, if needed
        :return: the trial's data directory
        """
        upper = trial_num // 1000
        lower = trial_num % 1000

        trial_dir = pathjoin(self.field_dir(field), 'trials', f"{upper:03d}", f"{lower:03d}")

        if mkdir:
            mkdirs(trial_dir)

        return trial_dir

    def metadata_path(self):
        return pathjoin(self.pathname, META_DATA_FILE)

    def chosen_fields(self):
        a = self.analysis
        names = self.field_names
        fields = [a.get_field(name) for name in names] if names else a.fields()
        return fields

    def lookup(self, full_name, field):
        class_name, attr_name = split_attr_name(full_name)

        if class_name == 'Field':
            obj = field

        elif class_name == 'Analysis':
            obj = self.analysis

        else:
            obj = field.find_process(class_name)
            if obj is None:
                raise McsUserError(f"A process of class '{class_name}' was not found in {field}")

        attr_obj = obj.attr_dict.get(attr_name)
        if attr_obj is None:
            raise McsUserError(f"The attribute '{attr_name}' was not found in '{obj}'")

        return attr_obj

    # TBD: need a way to specify correlations
    def generate(self, corr_mat=None):
        """
        Generate simulation data for the given ``Analysis``.

        :param corr_mat: a numpy matrix representing the correlation
           between each pair of parameters. corrMat[i,j] gives the
           desired correlation between the i'th and j'th entries of
           the parameter list.
        :return: none
        """
        trials = self.trials

        for field in self.chosen_fields():
            cols = []
            rv_list = []
            distributions = Distribution.distributions()

            for dist in distributions:
                target_attr = self.lookup(dist.full_name, field)

                # If the object has an explicit value for an attribute, we ignore the distribution
                if target_attr.explicit:
                    _logger.debug(f"{field} has an explicit value for '{dist.attr_name}'; ignoring distribution")
                    continue

                rv_list.append(dist.rv)
                cols.append(dist.attr_name if dist.class_name == 'Field' else dist.full_name)

            self.trial_data_df = df = lhs(rv_list, trials, columns=cols, corrMat=corr_mat)
            df.index.name = 'trial_num'
            self.save_trial_data(field)

    def save_trial_data(self, field):
        filename = self.trial_data_path(field, mkdir=True)
        self.trial_data_df.to_csv(filename)

    def consolidate_results(self):
        """
        Walk the trial directories, accumulating results into a single top-level
        results file.

        :return: the pathname of the results file.
        """
        pass

    def field_trial_data(self, field):
        """
        Read the trial data CSV from the top-level directory and return the DataFrame.
        The data is cached in the ``Simulation`` instance for re-use.

        :param field: (opgee.Field) the field to read data for
        :return: (pd.DataFrame) the values drawn for each field, parameter, and trial.
        """
        # TBD: allow option of using same draws across fields.

        if self.trial_data_df is not None:
            return self.trial_data_df

        path = self.trial_data_path(field)
        if not os.path.lexists(path):
            raise McsSystemError(f"Can't read trial data: '{path}' doesn't exist.")

        try:
            df = pd.read_csv(path, index_col='trial_num')

        except Exception as e:
            raise McsSystemError(f"Can't read trial data from '{path}': {e}")

        self.trial_data_df = df
        return df

    def trial_data(self, field, trial_num):
        """
        Return the values for all parameters for trial ``trial_num``.

        :param trial_num: (int) trial number
        :return: (pd.Series) the values for all parameters for the given trial.
        """
        df = self.field_trial_data(field)  # load data file on demand

        if trial_num not in df.index:
            path = self.trial_data_path(field)
            raise McsSystemError(f"Trial {trial_num} was not found in '{path}'")

        s = df.loc[trial_num]
        return s

    def set_trial_data(self, field, trial_num):
        data = self.trial_data(field, trial_num)

        for name, value in data.iteritems():
            attr = self.lookup(name, field)
            attr.explicit = True
            attr.set_value(value)

        self.analysis._after_init()
        field._after_init()

    def run_field(self, field, trial_nums):

        analysis = self.analysis

        results = []
        digits = 3

        for trial_num in trial_nums:
            _logger.debug(f"Running trial {trial_num} for {field}")
            self.set_trial_data(field, trial_num)

            try:
                field.run(analysis)
                field.report()
            except ModelValidationError as e:
                _logger.error(f"Skipping trial {trial_num}: {e}")
                continue

            # TBD: Save results (which?)
            # energy: Series dtype = "mmbtu/d"
            # emissions: DataFrame: cols are categories (Combustion, Land-use, Venting, Flaring, Fugitives, Other)
            #                       rows are (VOC, CO, CH4, N2O, CO2, GHG)
            # ghgs: Quantity "t/d" CO2e
            # ci: Quantity "g/MJ" CO2e
            #
            energy = field.energy.data
            emissions = field.emissions.data

            ghg = emissions.loc['GHG']
            total_ghg = ghg.sum()
            ci = field.compute_carbon_intensity(analysis)

            tup = (trial_num,
                   round(ci.m, digits),
                   round(total_ghg.m, digits),
                   round(ghg['Combustion'].m, digits),
                   round(ghg['Land-use'].m, digits),
                   round((ghg['Venting'] + ghg['Flaring'] + ghg['Fugitives']).m, digits),
                   round(ghg['Other'].m, digits))

            results.append(tup)

        cols = ['trial_num',
                'CI',
                'total_GHG',
                'combustion',
                'land_use',
                'VFF',
                'other']

        df = pd.DataFrame.from_records(results, columns=cols)
        mkdirs(self.results_dir)
        pathname = pathjoin(self.results_dir, field.name + '.csv')
        _logger.info(f"Writing '{pathname}'")
        df.to_csv(pathname, index=False)


    def run(self, trial_nums):
        """
        Run the given Monte Carlo trials for ``analysis``. If ``fields`` is
        ``None``, all fields are run, otherwise, only the indicated fields are
        run.

        :param trial_nums: (list of int) trials to run
        :param fields: (list of str) names of fields to run
        :return: none
        """
        for field in self.chosen_fields():
                self.run_field(field, trial_nums)

            # results for a field in `analysis`. Each column represents the results
            # of a single output variable. Each row represents the value of all output
            # variables for one trial of a single field. The field name is thus
            # included in each row, allowing results for all fields in a single
            # analysis to be stored in one file.


