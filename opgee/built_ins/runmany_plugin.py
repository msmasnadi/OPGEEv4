"""
.. Temporary plugin to run many (e.g., thousands) of fields in parallel using dask.

.. codeauthor:: <rich@plevin.com>

.. Copyright (c) 2021  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..subcommand import SubcommandABC

class RunManyCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Run thousands of fields in parallel using dask.'''}
        super().__init__('runmany', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        from ..utils import ParseCommaList

        parser.add_argument('-a', '--analysis',
                            help='''The name to give the <Analysis> element. Default is the file basename 
                            with the extension removed. Default is the first analyses found in the given 
                            model XML file.''')

        parser.add_argument('-b', '--batch-start', default=0, type=int,
                            help='''The value to use to start numbering batch result files.
                            Default is zero. Ignored unless -N/--save-after is specified.''')

        parser.add_argument('-f', '--fields', action=ParseCommaList,
                            help=f'''A comma-delimited list of fields to run. Default is to
                            run all fields indicated in the named analysis.''')

        parser.add_argument('-m', '--model', required=True,
                            help=f'''[Required] The pathname of a model XML file to process.''')

        parser.add_argument('-N', '--save-after', type=int,
                            help='''Write a results to a new file after the given number of results are 
                            returned. Implies --parallel.''')

        parser.add_argument('-n', '--count', type=int, default=0,
                            help='''The number of fields to run from the named analysis.
                            Default is 0, which means run all fields.''')

        parser.add_argument('-o', '--output', required=True,
                            help='''[Required] The pathname of the CSV files to create containing energy and 
                            emissions results for each field. This argument is used as a basename,
                            with the suffix '.csv' replaced by '-energy.csv' and '-emissions.csv' to
                            store the results. Each file has fields in columns and processes in rows.''')

        parser.add_argument('-p', '--parallel', action='store_true',
                            help='''Run the fields in parallel locally using dask.''')

        parser.add_argument('-S', '--start-with',
                            help='''The name of a field to start with. Use this to resume a run after a failure.
                            Can be combined with -n/--count to run a large number of fields in smaller batches.''')

        parser.add_argument('-s', '--skip-fields', action=ParseCommaList,
                            help='''Comma-delimited list of field names to exclude from analysis''')

        return parser

    def run(self, args, tool):
        from ..mcs.simulation import run_many

        run_many(args.model, args.analysis, args.fields, args.output, count=args.count,
            start_with=args.start_with, save_after=args.save_after, skip_fields=args.skip_fields,
            batch_start=args.batch_start, parallel=args.parallel)


