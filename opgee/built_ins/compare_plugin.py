#
# Generate and compare CSV files of process-level results for a set of fields.
# Usually used to compare with similar output from Excel (OPGEEv3) and here (OPGEEv4).
#
from opgee.subcommand import SubcommandABC

# Convert OPGEEv3 (Excel) process names to OPGEEv4 names
process_translator = {
    'foo' : 'bar',
}

class CompareCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Compare result CSV files''',
                  'description' : '''Compare CSV files with fields in columns and processes in row,
                      with the value either blank for disabled processes, or the total energy use per
                      day by process, after running the model. Mainly used for testing against OPGEEv3.
                      Note that CSV files for comparison can be generated using
                      "opg run --comparisonCSV filename".'''}

        super().__init__('compare', subparsers, kwargs)

    def addArgs(self, parser):
        '''
        Process the command-line arguments for this sub-command
        '''
        default_fractional_diff = 0.01    # < 1% difference is considered "close enough"

        parser.add_argument('file1',
                            help='''A CSV file containing results for comparison against "file2"''')

        parser.add_argument('file2',
                            help='''A CSV file containing results for comparison against "file1"''')

        parser.add_argument('-n', '--count', type=int, default=0,
                            help='''The number of fields to compare. Default is 0, which 
                                means compare all fields.''')

        parser.add_argument('-m', '--max-diff', type=float, default=default_fractional_diff,
                            help=f'''The maximum (fractional) difference in values for "file2" 
                                relative to "file1" that are deemed "approximately the same". 
                                Default is {default_fractional_diff}, 
                                i.e., (file2_value - file1_value) / file1_value <= {default_fractional_diff}''')

        parser.add_argument('-v', '--verbose', action='store_true',
                            help='''Report all value differences. By default, only field differences are reported.''')

        return parser

    def run(self, args, tool):
        import pandas as pd

        file1 = args.file1
        file2 = args.file2

        def read_results(filename):
            df = pd.read_csv(filename, index_col='process')
            df = df.rename(index=process_translator).sort_index(axis='rows')
            return df

        df1 = read_results(file1)
        df2 = read_results(file2)

        def compare_sets(iter1, iter2, name):
            s1 = set(iter1)
            s2 = set(iter2)

            if len(iter1) != len(iter2) or s1 != s2:
                print(f"{name} lists in the two result files differ")
                extra1 = s1 - s2
                extra2 = s2 - s1
                if extra1:
                    print(f"{file1} has items not in {file2}: {extra1}")
                if extra2:
                    print(f"{file2} has items not in {file1}: {extra2}")

                return False

            return True

        #
        # First, check that both files list the same set of processes
        #
        if not compare_sets(df1.index, df2.index, "Process"):
            return

        #
        # Next, check that the field names match
        #
        count    = args.count
        max_diff = args.max_diff
        verbose  = args.verbose

        if count:
            # limit comparison to the first "count" fields
            df1 = df1[df1.columns[:count]]
            df2 = df2[df2.columns[:count]]

        # Check that the files contain the same fields
        if not compare_sets(df1.columns, df2.columns, "Field"):
            return

        #
        # Finally, check that the individual process values match, for each field.
        # More specifically, the total energy consumption value for each process in
        # a field must be within "max_diff" of the value in the baseline for the
        # same field and process. Report fields that differ, and if --verbose was
        # selected, report the actual value differences as well.
        #
        for field, values1 in df1.iteritems():
            values2 = df2[field]

            na1 = values1.isna()
            na2 = values2.isna()
            comp = na1 == na2
            if not comp.all():
                print(f"Field '{field}' has NA values in different locations in the two files")
                if verbose:
                    na_procs1 = list(values1.index[na1])
                    na_procs2 = list(values2.index[na2])
                    print(f"   file1 has NA values for processes {na_procs1}")
                    print(f"   file2 has NA values for processes {na_procs2}")
                continue

            diffs = abs((values2 - values1)/values1)
            mismatches = diffs > max_diff
            if mismatches.any():
                print(f"Field {field} values differ")
                if verbose:
                    print(f"   file1 has {values1[mismatches].to_string(header=False)}")
                    print(f"   file2 has {values2[mismatches].to_string(header=False)}")

            if verbose:
                print(f"Field '{field}' matches")

# An alternative to naming the class 'Plugin' is to assign the class to PluginClass
PluginClass = CompareCommand
