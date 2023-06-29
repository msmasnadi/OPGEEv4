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
                            help='''Generate trial data for the specified field or fields only. Argument 
                            may be a comma-delimited list of Field names. Otherwise trial data is generated
                            for all fields defined in the analysis.''')

        parser.add_argument('-s', '--simulation-dir',
                            help='''The top-level directory to create for this simulation "package". 
                            If the simulation directory already exists and you must specify –-overwrite,
                            or gensim will refuse to overwrite the directory.''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from opgee.mcs.simulation import combine_results

        combine_results(args.simulation_dir, args.fields, args.delete)
