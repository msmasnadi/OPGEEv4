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
import traceback

from ..config import pathjoin
from ..constants import SIMPLE_RESULT, ERROR_RESULT
from ..core import OpgeeObject, split_attr_name
from ..error import OpgeeException, McsSystemError, McsUserError, CommandlineError
from ..field import FieldResult
from ..log import getLogger
from ..model_file import ModelFile
from ..pkg_utils import resourceStream
from ..utils import mkdirs, removeTree

from .distro import get_frozen_rv
from .LHS import lhs

_logger = getLogger(__name__)

TRIAL_DATA_CSV = 'trial_data.csv'
RESULTS_CSV = 'results.csv'
FAILURES_CSV = 'failures.csv'
MODEL_FILE = 'merged_model.xml'
META_DATA_FILE = 'metadata.json'

DISTROS_CSV = 'mcs/etc/parameter_distributions.csv'

DEFAULT_DIGITS = 3

def roundmag(quantity, digits=DEFAULT_DIGITS):          # pragma: no cover
    return round(quantity.m, digits)

def model_file_path(sim_dir):     # pragma: no cover
    model_file = pathjoin(sim_dir, MODEL_FILE)
    return model_file

# Deprecated in favor of XML (see mcs/parameter_list.py)
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

            if low == '' or high == '':     # must specify both low and high
                rv = get_frozen_rv('lognormal', logmean=mean, logstdev=stdev)
            else:
                rv = get_frozen_rv('truncated_lognormal', logmean=mean, logstdev=stdev, low=low, high=high)

        elif shape == 'empirical':
            rv = get_frozen_rv('empirical', pathname=pathname, colname=name)

        else:
            raise McsSystemError(f"Unknown distribution shape: '{shape}'")

        # merge CSV-based distros with decorator-based ones
        Distribution(name, rv)


class Distribution(OpgeeObject):

    instances = {}

    def __init__(self, full_name, rv):
        self.full_name = full_name
        try:
            self.class_name, self.attr_name = split_attr_name(full_name)
        except OpgeeException as e:
            raise McsUserError(f"attribute name format is 'ATTR' (same as 'Field.ATTR) or 'CLASS.ATTR'; got '{full_name}'")

        self.rv = rv
        self.instances[full_name] = self

    @classmethod
    def distro_by_name(cls, name):
        return cls.instances.get(name)

    @classmethod
    def distributions(cls):
        """
        Return a list of the defined Distribution instances.

        :return: (list of opgee.mcs.Distribution) the instances
        """
        return cls.instances.values()

    def __str__(self):
        return f"<Distribution '{self.full_name}' = {self.rv}>"


class Simulation(OpgeeObject):
    # TBD: update this document string
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
      ``trials`` comprises two levels of 3-digit values, which, when concatenated, form the
      trial number. That is, trial 1,423 would be found in ``trials/001/423``. This allows
      up to 1 million trials while ensuring that no directory contains more than 1000 items.
      Limiting directory size improves performance.
    """
    def __init__(self, sim_dir, analysis_name=None, trials=0, field_names=None,
                 save_to_path=None, meta_data_only=False):

        if not os.path.isdir(sim_dir):
            raise McsUserError(f"Simulation directory '{sim_dir}' does not exist.")

        self.pathname = sim_dir
        self.model_file = model_file = model_file_path(sim_dir)
        self.model = None
        self.model_xml_string = None

        self.trial_data_df = None # loaded on demand by ``trial_data`` method.
        self.trials = trials

        self.analysis_name = analysis_name
        self.analysis = None
        self.field_names = field_names
        self.metadata = None

        if analysis_name:
            self._save_meta_data()
        else:
            self._load_meta_data(field_names)

        if trials > 0:
            self.generate()

        if meta_data_only:  # a slight misnomer since we may generate trial_data.csv, too
            return

        try:
            _logger.debug(f"Caching file '{model_file}' as xml_string")
            with open(model_file) as f:
                self.model_xml_string = f.read()
        except Exception as e:
            raise McsSystemError(f"Failed to read model file '{model_file}' to XML string: {e}")

        # TBD: to allow the same trial_num to be run across fields, cache field
        #      trial_data in a dict by field name rather than a single DF

        self.load_model(save_to_path=save_to_path)

    def load_model(self, save_to_path=None):
        """
        Loads the model (reading just the field being run by this Simulation) from XML
        to avoid carrying state between trials.

        :return: none
        """
        mf = ModelFile(self.model_file,
                       xml_string=self.model_xml_string,
                       use_default_model=False,
                       analysis_names=[self.analysis_name],
                       field_names=self.field_names,
                       save_to_path=save_to_path)
        self.model = mf.model

        self.analysis = self.model.get_analysis(self.analysis_name, raiseError=False)
        if not self.analysis:
            raise CommandlineError(f"Analysis '{self.analysis_name}' was not found in model")


    @classmethod
    def read_metadata(cls, sim_dir):
        """
        Used by runsim to get the field names without loading the whole simulation
        """
        sim = Simulation(sim_dir, meta_data_only=True)
        return sim.metadata

    def _save_meta_data(self):
        self.metadata = {
            'analysis_name': self.analysis_name,
            'trials'       : self.trials,
            'field_names'  : self.field_names,  # None => process all Fields in the Analysis
        }

        with open(self.metadata_path(), 'w') as fp:
            json.dump(self.metadata, fp, indent=2)

    def _load_meta_data(self, field_names):
        metadata_path = self.metadata_path()
        try:
            with open(metadata_path, 'r') as fp:
                self.metadata = metadata = json.load(fp)
        except Exception as e:
            raise McsUserError(f"Failed to load simulation '{metadata_path}' : {e}")

        if field_names:
            names = set(field_names)
            # Use list comprehension rather than set.intersection to maintain original order
            self.field_names = [name for name in metadata['field_names'] if name in names]
        else:
            self.field_names = metadata['field_names']

        self.analysis_name = metadata['analysis_name']
        self.trials        = metadata['trials']

    @classmethod
    def new(cls, sim_dir, model_files, analysis_name, trials,
            field_names=None, overwrite=False, use_default_model=True):
        """
        Create the simulation directory and the ``sandboxes`` subdirectory.

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

        mf = ModelFile(model_files, use_default_model=use_default_model,
                       save_to_path=merged_model_file,
                       instantiate_model=False) # avoid building potentially huge model

        # Find needed info in the parsed XML so we can avoid instantiating potentially
        # huge models. (E.g., the 9000 field test case produced a 200+ MB XML file.)

        analysis_node = mf.root.find(f"./Analysis[@name='{analysis_name}']")
        if analysis_node is None:
            raise McsUserError(f"Analysis '{analysis_name}' was not found in model")

        groups = analysis_node.xpath("Group")
        if groups:
            raise McsUserError("Simulation does not yet support use of <Group>")
            # TODO:
            #   if group.attrib.get('regex', False)
            #     prog = re.compile(group.text)
            #     matches = [field for field in field_names for name in field.group_names if prog.match(group_name)]

        field_names = field_names or analysis_node.xpath("FieldRef/@name")

        # analysis = mf.model.get_analysis(analysis_name, raiseError=False)
        # if not analysis:
        #     raise McsUserError(f"Analysis '{analysis_name}' was not found in model")
        #
        # field_names = field_names or analysis.field_names(enabled_only=True)

        sim = cls(sim_dir, analysis_name=analysis_name, field_names=field_names,
                  trials=trials, meta_data_only=True)
        return sim

    # Class method to be callable from distributed_mcs_dask.py's run_field
    @classmethod
    def field_dir_path(cls, sim_dir, field_name):
        d = pathjoin(sim_dir, field_name)
        return d

    def field_dir(self, field):
        from opgee.field import Field

        field_name = field.name if isinstance(field, Field) else field
        d = self.field_dir_path(self.pathname, field_name)
        return d

    def trial_data_path(self, field, mkdir=False):
        d = self.field_dir(field)
        if mkdir:
            mkdirs(d)
        path = pathjoin(d, TRIAL_DATA_CSV)
        return path

    def results_path(self, field, packet_num, mkdir=False):
        d = self.field_dir(field)
        if mkdir:
            mkdirs(d)

        filename = RESULTS_CSV if packet_num is None else f"results-{packet_num}.csv"
        path = pathjoin(d, filename)
        return path

    def failures_path(self, field, packet_num):
        d = self.field_dir(field)
        filename = FAILURES_CSV if packet_num is None else f"failures-{packet_num}.csv"
        path = pathjoin(d, filename)
        return path

    def metadata_path(self):
        return pathjoin(self.pathname, META_DATA_FILE)

    def chosen_fields(self):
        a = self.analysis
        names = self.field_names
        fields = [a.get_field(name) for name in names] if names else a.fields()
        return fields

    def lookup(self, full_name, field):
        class_name, attr_name = split_attr_name(full_name)

        if class_name is None or class_name == 'Field':
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

        for field_name in self.field_names:
            cols = []
            rv_list = []
            distributions = Distribution.distributions()

            for dist in distributions:
                rv_list.append(dist.rv)
                cols.append(dist.attr_name if dist.class_name == 'Field' else dist.full_name)

            self.trial_data_df = df = lhs(rv_list, trials, columns=cols, corrMat=corr_mat)
            df.index.name = 'trial_num'
            self.save_trial_data(field_name)

    def save_trial_data(self, field_name):
        filename = self.trial_data_path(field_name, mkdir=True)
        _logger.info(f"Writing '{filename}'")
        self.trial_data_df.to_csv(filename)

    # Deprecated
    # def save_trial_results(self, field, df, packet_num, failures):
    #     """
    #     Save the results of an MCS "trial packet" (which may be all trials
    #     for ``field`` or just a subset of trials) to a CSV file in the simulation
    #     directory.
    #
    #     :param field: (opgee.Field) the Field to evaluate in MCS
    #     :param df: (pandas.DataFrame) the results to save
    #     :param packet_num: (int) The sequential number for this packet in
    #         ``field``. If not None, this is used to name the result files.
    #     :param failures: (list of tuples) tuples of form (trial_num, message)
    #         for each failed trial.
    #     :return: nothing
    #     """
    #     filename = self.results_path(field, packet_num, mkdir=True)
    #     _logger.info(f"Writing '{filename}'")
    #     df.to_csv(filename, index=False)
    #
    #     # Save info on failed trials, too
    #     failures_csv = self.failures_path(field, packet_num)
    #     _logger.info(f"Writing {len(failures)} failures to '{failures_csv}'")
    #     with open(failures_csv, 'w') as f:
    #         f.write("trial_num,message\n")
    #         for trial_num, msg in failures:
    #             f.write(f'{trial_num},"{msg}"\n')

    def field_trial_data(self, field):
        """
        Read the trial data CSV from the top-level directory and return the DataFrame.
        The data is cached in the ``Simulation`` instance for re-use.

        :param field: (opgee.Field  or str) a field instance or name to read data for
        :return: (pd.DataFrame) the values drawn for each field, parameter, and trial.
        """
        # TBD: allow option of using same draws across fields?

        if isinstance(field, str):
            field = self.analysis.get_field(field)

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

    def set_trial_data(self, analysis, field, trial_num):
        from ..smart_defaults import SmartDefault

        _logger.debug(f"set_trial_data for field {field.name}, trial {trial_num}")
        data = self.trial_data(field, trial_num)

        for name, value in data.items():
            attr = self.lookup(name, field)
            if not attr.explicit:               # don't set values of explicit attributes
                attr.explicit = True
                attr.set_value(value)

        # TBD: test this
        SmartDefault.apply_defaults(field, analysis=analysis)

    def run_packet(self, packet, result_type=SIMPLE_RESULT):
        """
        Run the Monte Carlo trials ``trial_nums` for ``field``, serially.
        Save the (full or partial) results for this field to a CSV file in
        the simulation directory.

        :param packet: (TrialPacket) info describing a set of model runs to execute.
        :param result_type: (str) either SIMPLE_RESULT or DETAILED_RESULT.
        :return: (list of FieldResult) describing results for trials indicated
            by ``packet``.
        """
        field_name = packet.field_name

        results = []

        for trial_num in packet:
            try:
                # Reload from cached XML string to avoid stale state
                self.load_model()
                analysis = self.analysis

                # Use the new instance of field from the reloaded model
                field = analysis.get_field(field_name)

                self.set_trial_data(analysis, field, trial_num)

                field.run(analysis, compute_ci=True, trial_num=trial_num)
                result = field.get_result(analysis, result_type, trial_num=trial_num)
                results.append(result)

            except Exception as e:
                errmsg = f"Trial {trial_num}: {e}"
                result = FieldResult(self.analysis.name, field_name, ERROR_RESULT,
                                     trial_num=trial_num, error=errmsg)
                results.append(result)

                _logger.warning(f"Exception raised in trial {trial_num} in {field_name}: {e}")
                _logger.debug(traceback.format_exc())
                continue

        return results
