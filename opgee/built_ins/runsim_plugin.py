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

MODE_CLUSTER = 'cluster'
MODE_LOCAL = 'local'
KNOWN_MODES = [MODE_CLUSTER, MODE_LOCAL]

class RunsimCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : 'Run a Monte Carlo simulation using the model file stored in the simulation folder.'}
        super(RunsimCommand, self).__init__('runsim', subparsers, kwargs)

    def addArgs(self, parser):
        from ..config import getParam
        from ..utils import ParseCommaList

        log_file  = getParam('OPGEE.LogFile')
        job_name  = getParam('SLURM.JobName')
        load_env  = getParam('SLURM.LoadEnvironment')
        partition = getParam('SLURM.Partition')
        min_per_task = getParam('SLURM.MinutesPerTask')

        # parser.add_argument('-a', '--analysis',
        #                     help='''The name of the analysis to run''')
        #
        # parser.add_argument('--overwrite', action='store_true',
        #                     help='''OVERWRITE prior results, if any.''')

        cluster_types = ('local', 'slurm')
        cluster_type = getParam('OPGEE.ClusterType')
        parser.add_argument('-c', '--cluster-type', choices=cluster_types,
                            help=f'''The type of cluster to use. Defaults to value of config
                            variable 'OPGEE.ClusterType', currently "{cluster_type}".''')

        # parser.add_argument('-E', "--load-env", default="",
        #                     help=f'''A command to load your python and/or module environment. Default
        #                         is the value of config variable "SLURM.LoadEnvironment, currently
        #                         '{load_env}'".''')

        parser.add_argument('-f', '--fields', action=ParseCommaList,
                            help='''Run only the specified field or fields. Argument may be a 
                            comma-delimited list of Field names. Otherwise all fields defined in the
                            analysis are run.''')

        parser.add_argument('-m', '--minutes', default=min_per_task,
                            help=f'''The amount of wall time to allocate for each task. Default is 
                                {min_per_task} minutes. Acceptable time formats include "minutes", 
                                "minutes:seconds", "hours:minutes:seconds", and formats involving days, 
                                which we shouldn't require.''')

        parser.add_argument('-n', "--ntasks", type=int, default=None,
                            help='''Number of worker tasks to create. Default is the number of fields, if
                                specified using -f/--fields, otherwise -n/--ntasks is required.''')

        parser.add_argument('-p', "--partition", default=None,
                            help=f'''The name of the partition to use for job submissions. Default is the
                                 value of config variable "SLURM.Partition", currently '{partition}'.''')

        parser.add_argument('-s', '--simulation-dir',
                            help='''The top-level directory to use for this simulation "package"''')

        parser.add_argument('-S', '--serial', action='store_true',
                            help="Run the simulation serially in the currently running process.")

        parser.add_argument('-t', '--trials', default='all',
                            help='''The trials to run. Can be expressed as a string containing
                            comma-delimited ranges and individual trail numbers, e.g. "1-20,22, 35, 42, 44-50").
                            The special string "all" (the default) runs all defined trials.''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from ..error import OpgeeException
        from ..utils import parseTrialString
        from ..mcs.simulation import Simulation
        from ..mcs.distributed_mcs_dask import Manager

        sim_dir = args.simulation_dir
        field_names = args.fields       # TBD: if not set, get fields from XML
        ntasks = args.ntasks

        if ntasks is None:
            if field_names:
                ntasks = len(field_names)
            else:
                raise OpgeeException(f"Must specify field names (-f/--fields) or -n/--ntasks")

        if args.serial:
            sim = Simulation(sim_dir, field_names=field_names)
            trial_nums = (None if args.trials == 'all' else parseTrialString(args.trials))
            sim.run(trial_nums)

        else:
            mgr = Manager(cluster_type=args.cluster_type)
            mgr.run_mcs(sim_dir, field_names=field_names, num_engines=ntasks,
                        trial_nums=args.trials, minutes_per_task=args.minutes)
