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
        parser.add_argument('-a', '--analysis',
                            help='''The name of the analysis to run''')

        parser.add_argument('--overwrite', action='store_true',
                            help='''OVERWRITE prior results, if any.''')

        parser.add_argument('-s', '--simulation_dir',
                            help='''The top-level directory to use for this simulation "package"''')

        parser.add_argument('-t', '--trials', type=int, default=0,
                            help='''The number of trials to run. Must be <= the number specified when 
                            creating this simulation. By default, all defined trials are run.''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from ..error import McsUserError
        from ..mcs.simulation import Simulation

        if args.trials <= 0:
            raise McsUserError("Trials argument must be an integer > 0")

        # TBD: Load the model so we can access the attribute dictionary
        attr_dict = None

        sim = Simulation(args.simulation_dir, overwrite=args.overwrite)

        # TBD: pass Analysis instance rather than name and attr_dict?
        sim.generate(args.analysis, args.trials, attr_dict)
