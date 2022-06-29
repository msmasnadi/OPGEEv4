#
# Plugin to generate empirical data files for WOR by age ranges
#
# Author: Richard Plevin
#
# Copyright (c) 2022 the author and The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..log import getLogger
from ..subcommand import SubcommandABC

_logger = getLogger(__name__)

DEFAULT_DATAFILE = 'mcs/etc/WOR_observations.csv'

class GenworCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : 'Extract empirical distributions from WOR data based on field age.'}
        super(GenworCommand, self).__init__('genwor', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('output_file',
                            help='''The long-form CSV file to create containing the observation data.''')

        parser.add_argument('-i', '--input_file',
                            help=f'''The CSV file containing WOR data by age (rows are ages; cols are fields or field groups).
                                     Default file is '{DEFAULT_DATAFILE} from within the OPGEEv4 package.''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        import pandas as pd
        from opgee.pkg_utils import resourceStream

        # Read internal file by default, otherwise the user's given file
        csvfile = args.input_file or resourceStream(DEFAULT_DATAFILE, stream_type='bytes', decode=None)

        df = pd.read_csv(csvfile, index_col='Year').fillna('')

        records = []
        for col_name, col_series in df.iteritems():
            observations = [(col_name, age, wor) for age, wor in col_series.iteritems() if wor != '']
            records.extend(observations)

        long_df = pd.DataFrame.from_records(records, columns=['name', 'age', 'WOR'])
        long_df.to_csv(args.output_file, index=False)

        #
        # Combine all the data
        #
        etc_dir = '/Users/rjp/repos/OPGEEv4/opgee/mcs/etc/'

        norway_csv = etc_dir + 'Norway_historical_WOR.csv'
        uk_csv = etc_dir + 'UK_Results_MATLAB.csv'
        orig_csv = etc_dir + 'WOR_observations_long.csv'

        norway_df = pd.read_csv(norway_csv)
        norway_df.drop('year', axis='columns', inplace=True)
        uk_df = pd.read_csv(uk_csv)
        orig_df = pd.read_csv(orig_csv)

        all_wor = pd.concat([orig_df, norway_df, uk_df], axis="rows").dropna(axis='rows')
        has_inf = all_wor.query("WOR == inf")
        all_wor.drop(has_inf.index, axis="rows", inplace=True)

        all_csv = etc_dir + 'all_wor.csv'
        all_wor.to_csv(all_csv, index=False)

        # all_csv = etc_dir + 'all_wor.csv'
        # all_wor = pd.read_csv(all_csv, index_col=False)

        records = []
        for age in sorted(all_wor.age.unique()):
            df = all_wor.query("age == @age")
            wor = df.WOR
            # convert negative WOR values to zero
            records.append((age, max(0,0, wor.min()), wor.max()))

        df = pd.DataFrame.from_records(records, columns=['age', 'min', 'max'])

        ranges_csv = etc_dir + 'wor_ranges.csv'
        df.to_csv(ranges_csv, index=False)

#
# WOR: lognormal(mean=4.021*EXP(0.024*Field_age)-4.021, std=0.012*Field_age^1.6622, low_bound=0, high_bound=33.37)
#
# def wor_distro(age):
#     from math import exp
#     from ..mcs.distro import get_frozen_rv
#
#     mean  = 4.021 * exp(0.024 * age) - 4.021
#     stdev = 0.012 * age ** 1.6622
#     rv = get_frozen_rv('lognormal', logmean=mean, logstdev=stdev)
#     return rv
