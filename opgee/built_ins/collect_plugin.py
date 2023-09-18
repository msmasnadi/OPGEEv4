#
# Author: Richard Plevin
#
# Copyright (c) 2023 the author and The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..log import getLogger
from ..subcommand import SubcommandABC

_logger = getLogger(__name__)

class CollectCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : 'Collect partial results from packets of trials in a Monte Carlo simulation.'}
        super().__init__('collect', subparsers, kwargs)

    def addArgs(self, parser):
        from ..utils import ParseCommaList

        parser.add_argument('-d', '--delete', action='store_true',
                            help='''Delete the partial result files after combining them into a single file.''')

        parser.add_argument('-f', '--fields', action=ParseCommaList,
                            help='''The names of the field to operate on. If not provided, all partial
                            result files found will be combined.''')

        parser.add_argument('-o', '--output-dir',
                            help='''The directory containing partial result files. Use only for non-MCS results.
                            For MCS, use the -s/--sim-dir option.''')

        parser.add_argument('-s', '--sim-dir',
                            help='''The simulation directory. Use for Monte Carlo Simulations only. For
                            non-MCS results, use the -o/--output-dir option.''')



        return parser   # for auto-doc generation


    def run(self, args, tool):
        from ..manager import combine_mcs_results, combine_field_results

        if args.sim_dir:
            combine_mcs_results(args.sim_dir, args.fields, args.delete)
        else:
            combine_field_results(args.output_dir, args.fields, args.delete)

