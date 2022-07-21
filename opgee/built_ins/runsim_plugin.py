#
# "runsim" sub-command to run a Monte Carlo simulation
#
# Author: Richard Plevin
#
# Copyright (c) 2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..log import getLogger
from ..subcommand import SubcommandABC

_logger = getLogger(__name__)

class RunsimCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : 'Run a Monte Carlo simulation using the model file stored in the simulation folder.'}
        super(RunsimCommand, self).__init__('runsim', subparsers, kwargs)

    def addArgs(self, parser):
        from ..utils import ParseCommaList

        # parser.add_argument('-a', '--analysis',
        #                     help='''The name of the analysis to run''')
        #
        # parser.add_argument('--overwrite', action='store_true',
        #                     help='''OVERWRITE prior results, if any.''')

        parser.add_argument('-c', '--cpu_count', type=int, default=0,
                            help='''The number of CPUs to use to run the MCS. A value of
                            zero means use all available CPUs. This flag implies -d/--distributed.''')

        parser.add_argument('-d', '--distributed', action='store_true',
                            help='''Run the MCS in distributed mode, using all available CPUs,
                               or the number indicated with the -c/--cpus argument.''')

        parser.add_argument('-f', '--fields', action=ParseCommaList,
                            help='''Run only the specified field or fields. Argument may be a 
                            comma-delimited list of Field names. Otherwise all fields defined in the
                            analysis are run.''')

        parser.add_argument('-s', '--simulation_dir',
                            help='''The top-level directory to use for this simulation "package"''')

        parser.add_argument('-t', '--trials', default='all',
                            help='''The trials to run. Can be expressed as a string containing
                            comma-delimited ranges and individual trail numbers, e.g. "1-20,22, 35, 42, 44-50").
                            The special string "all" (the default) runs all defined trials.''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from ..utils import parseTrialString
        from ..mcs.simulation import Simulation
        from ..mcs.distributed_mcs import Manager

        sim_dir = args.simulation_dir
        field_names = args.fields

        if args.distributed or args.cpu_count:
            mgr = Manager()
            mgr.run_mcs(sim_dir, field_names=field_names, cpu_count=args.cpu_count)
        else:
            sim = Simulation(sim_dir, field_names=field_names)
            trial_nums = (range(sim.trials) if args.trials == 'all'
                          else parseTrialString(args.trials))
            sim.run(trial_nums)
