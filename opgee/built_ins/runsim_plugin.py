#
# "runsim" sub-command to run a Monte Carlo simulation
#
# Author: Richard Plevin
#
# Copyright (c) 2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
from ..subcommand import SubcommandABC

class RunsimCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : 'Run a Monte Carlo simulation using the model file stored in the simulation folder.'}
        super().__init__('runsim', subparsers, kwargs)

    def addArgs(self, parser):
        from ..config import getParam, getParamAsInt
        from ..utils import ParseCommaList, positive_int
        from ..field import RESULT_TYPES, DEFAULT_RESULT_TYPE, SIMPLE_RESULT, DETAILED_RESULT

        partition = getParam('SLURM.Partition')
        min_per_task = getParam('SLURM.MinutesPerTask')
        packet_size = getParamAsInt('OPGEE.MaxTrialsPerPacket')

        cluster_types = ('local', 'slurm')
        cluster_type = getParam('OPGEE.ClusterType')
        parser.add_argument('-c', '--cluster-type', choices=cluster_types,
                            help=f'''The type of cluster to use. Defaults to value of config
                            variable 'OPGEE.ClusterType', currently "{cluster_type}".''')
        #
        # User can specify fields by name, or the number of fields to run MCS for, but not both.
        #
        group = parser.add_mutually_exclusive_group()

        group.add_argument('-f', '--fields', action=ParseCommaList,
                            help='''Run only the specified field or fields. Argument may be a 
                            comma-delimited list of Field names. Otherwise all fields defined in the
                            analysis are run. (Mutually exclusive with -N/--nfields.)''')

        group.add_argument('-N', "--num-fields", type=positive_int, default=None,
                           help='''Run MCS simulations on the first "num-fields" only.
                            (Mutually exclusive with -f/--fields.)''')

        parser.add_argument('-C', '--collect', action='store_true',
                            help='''Whether to combine per-packet files into a single CSV when
                            simulation is complete. Note that the "collect" subcommand can do
                            this later if needed.''')

        parser.add_argument('-m', '--minutes', default=min_per_task, type=positive_int,
                            help=f'''The amount of wall time to allocate for each task. Default is 
                                {min_per_task} minutes. Acceptable time formats include "minutes", 
                                "minutes:seconds", "hours:minutes:seconds", and formats involving days, 
                                which we shouldn't require.''')

        parser.add_argument('-n', "--ntasks", type=positive_int, default=None,
                            help='''Number of worker tasks to create. Default is the number of fields, if
                                specified using -f/--fields, otherwise -n/--ntasks is required.''')

        parser.add_argument('-p', "--partition", default=None,
                            help=f'''The name of the partition to use for job submissions. Default is the
                                 value of config variable "SLURM.Partition", currently '{partition}'.''')

        parser.add_argument('-P', '--packet-size', type=positive_int, default=packet_size,
                            help=f'''Divide trials for a single field in to packets of this number of trials
                            to run serially on a single worker. Default is the value of configuration file
                            parameter "OPGEE.TrialPacketSize", currently {packet_size}.'''),

        parser.add_argument('-r', '-result-type', type=str, choices=RESULT_TYPES,
                            help=f'''The type of result to return from each field. Default is "{DEFAULT_RESULT_TYPE}".
                            For "{SIMPLE_RESULT}" results, the following values are saved per trial in a separate 
                            file for each field: trial_num, CI, total GHGs, and emissions from combustion, land use,
                            venting/flaring, other. For "{DETAILED_RESULT}" results, per-process emissions and energy
                            use are stored.''')

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
        from ..mcs.distributed_mcs_dask import Manager, run_field

        sim_dir = args.simulation_dir
        field_names = args.fields or []
        num_fields = args.num_fields
        ntasks = args.ntasks

        if not (ntasks or num_fields or field_names):
            raise OpgeeException(f"Must specify field names (-f/--fields), number of fields "
                                 f"(-N/--num-fields) or number of tasks (-n/--ntasks)")

        if not field_names:
            metadata = Simulation.read_metadata(sim_dir)
            field_names = metadata['field_names']

        if num_fields:
            field_names = field_names[:num_fields]

        if ntasks is None:
            ntasks = len(field_names)

        if args.serial:
            trial_nums = (None if args.trials == 'all' else parseTrialString(args.trials))
            for field_name in field_names:
                run_field(sim_dir, field_name, trial_nums=trial_nums)
        else:
            mgr = Manager(cluster_type=args.cluster_type)
            mgr.run_mcs(sim_dir, args.packet_size, field_names=field_names,
                        num_engines=ntasks, trial_nums=args.trials,
                        minutes_per_task=args.minutes,
                        collect=args.collect)
