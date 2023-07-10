"""
.. OPGEE "run" sub-command

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..subcommand import SubcommandABC
from ..log import getLogger

_logger = getLogger(__name__)

PARALLEL = 'parallel'
SERIES   = 'series'
RUN_MODES = (PARALLEL, SERIES)

def positive_int(value):
    import argparse

    try:
        i = int(value)
    except:
        i = 0   # the effect is to convert a ValueError into an ArgumentTypeError

    if i <= 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive integer")

    return i

class RunCommand(SubcommandABC):
    def __init__(self, subparsers, name='run', help='Run the specified portion of an OPGEE LCA model'):
        kwargs = {'help' : help}
        super(RunCommand, self).__init__(name, subparsers, kwargs)

    def addArgs(self, parser):
        from ..config import getParam, getParamAsInt
        from ..utils import ParseCommaList
        from ..mcs.simulation import RESULT_TYPES, DEFAULT_RESULT_TYPE, SIMPLE_RESULT, DETAILED_RESULT

        partition = getParam('SLURM.Partition')
        min_per_task = getParam('SLURM.MinutesPerTask')
        packet_size = getParamAsInt('OPGEE.MaxTrialsPerPacket')

        # User can specify fields by name, or the number of fields to run MCS for, but not both.
        group = parser.add_mutually_exclusive_group()

        parser.add_argument('-a', '--analyses', action=ParseCommaList,
                            help='''Run only the specified analysis or analyses. Argument may be a 
                            comma-delimited list of Analysis names.''')

        parser.add_argument('-A', '--save-after', type=int,
                            help='''Write a results to a new file after the given number of results are 
                            returned. Implies --parallel.''')

        parser.add_argument('-b', '--batch-start', default=0, type=int,
                            help='''The value to use to start numbering batch result files.
                            Default is zero. Ignored unless -N/--save-after is specified.''')

        parser.add_argument('-B', '--by-process',
                            help='''Write CI output to specified CSV file for all processes, for all fields 
                                run, rather than by top-level processes and aggregators (as with --output)''')

        cluster_types = ('local', 'slurm')
        cluster_type = getParam('OPGEE.ClusterType')
        parser.add_argument('-c', '--cluster-type', choices=cluster_types,
                            help=f'''The type of cluster to use. Defaults to value of config
                            variable 'OPGEE.ClusterType', currently "{cluster_type}".''')

        parser.add_argument('-C', '--collect', action='store_true',
                            help='''Whether to combine per-packet files into a single CSV when
                            simulation is complete. Note that the "collect" subcommand can do
                            this later if needed.''')

        parser.add_argument('-f', '--fields', action=ParseCommaList,
                            help='''Run only the specified field or fields. Argument may be a 
                            comma-delimited list of Field names. To specify a field within a specific 
                            Analysis, use the syntax "analysis_name.field_name". Otherwise the field 
                            will be run for each Analysis the field name occurs within (respecting the
                            --analyses flag).''')

        parser.add_argument('-i', '--ignore-errors', action='store_true',
                            help='''Keep running even if some fields raise errors when run''')

        parser.add_argument('-k', '--skip-fields', action=ParseCommaList,
                            help='''Comma-delimited list of field names to exclude from analysis''')

        parser.add_argument('-m', '--model-file', action='append',
                            help='''XML model definition files to load. If --no_default_model is *not* 
                                specified, the built-in files etc/opgee.xml and etc/attributes.xml are 
                                loaded first, and the XML files specified here will be merged with these.
                                If --no_default_model is specified, only the given files are loaded;
                                they are merged in the order stated.''')

        parser.add_argument('-M', '--minutes', default=min_per_task, type=positive_int,
                            help=f'''The amount of wall time to allocate for each task. Default is 
                                {min_per_task} minutes. Acceptable time formats include "minutes", 
                                "minutes:seconds", "hours:minutes:seconds", and formats involving days, 
                                which we shouldn't require.''')

        parser.add_argument('-n', '--no-default-model', action='store_true',
                            help='''Don't load the built-in opgee.xml model definition.''')

        group.add_argument('-N', "--num-fields", type=positive_int, default=None,
                           help='''Run MCS simulations on the first "num-fields" only.
                            (Mutually exclusive with -f/--fields.)''')

        parser.add_argument('-o', '--output',
                            help='''Write CI output to specified CSV file for all top-level processes 
                            and aggregators, for all fields run''')

        # parser.add_argument('-o', '--output', required=True,
        #                     help='''[Required] The pathname of the CSV files to create containing energy and
        #                     emissions results for each field. This argument is used as a basename,
        #                     with the suffix '.csv' replaced by '-energy.csv' and '-emissions.csv' to
        #                     store the results. Each file has fields in columns and processes in rows.''')

        parser.add_argument('-p', "--partition", default=None,
                            help=f'''The name of the partition to use for job submissions. Default is the
                                 value of config variable "SLURM.Partition", currently '{partition}'.''')

        parser.add_argument('-P', '--parallel', action='store_true',
                            help='''Run the fields in parallel locally using dask.''')

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

        parser.add_argument('-R', '--run-mode', choices=RUN_MODES, default=PARALLEL,
                            help=f'''Whether to run serially or in parallel by creating a dask cluster. 
                            Default is "{PARALLEL}" when running more than one field or trial.''')

        parser.add_argument('-s', '--simulation-dir',
                            help='''The top-level directory to use for this simulation "package"''')

        parser.add_argument('-S', '--serial', action='store_true',
                            help="Run the simulation serially in the currently running process.")

        parser.add_argument('-t', '--trials', default='all',
                            help='''The trials to run. Can be expressed as a string containing
                            comma-delimited ranges and individual trail numbers, e.g. "1-20,22, 35, 42, 44-50").
                            The special string "all" (the default) runs all defined trials.''')

        parser.add_argument('-T', "--ntasks", type=positive_int, default=None,
                            help='''Number of worker tasks to create. Default is the number of fields, if
                                specified using -f/--fields, otherwise -n/--ntasks is required.''')

        parser.add_argument('-v', '--save-comparison',
                            help='''The name of a CSV file to which to save results suitable for 
                                use with the "compare" subcommand.''')

        parser.add_argument('-w', '--start-with',
                            help='''The name of a field to start with. Use this to resume a run after a failure.
                            Can be combined with -n/--num-fields to run a large number of fields in smaller batches.''')

        return parser

    # TBD: this was the run() method from the runsim plugin.
    def runsim(self, args):
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


    def run(self, args, tool):
        from ..error import OpgeeException, CommandlineError

        from ..model_file import ModelFile

        # from ..mcs.simulation import run_many
        #
        # run_many(args.model_file, args.analysis, args.fields, args.output, count=args.num_fields,
        #     start_with=args.start_with, save_after=args.save_after, skip_fields=args.skip_fields,
        #     batch_start=args.batch_start, parallel=args.parallel)

        use_default_model = not args.no_default_model
        model_files = args.model_file
        field_names = args.fields
        analysis_names = args.analyses

        if not (field_names or analysis_names):
            raise CommandlineError("Must indicate one or more fields or analyses to run")

        if not (use_default_model or model_files):
            raise CommandlineError("No model to run: the --model-file option was not used and --no-default-model was specified.")

        mf = ModelFile(model_files, use_default_model=use_default_model,
                       analysis_names=analysis_names, field_names=field_names)
        model = mf.model

        all_analyses = model.analyses()
        if analysis_names:
            selected_analyses = [ana for ana in all_analyses if ana.name in analysis_names]
            if not selected_analyses:
                raise CommandlineError(f"Specified analyses {analysis_names} were not found in model")
        else:
            selected_analyses = list(all_analyses)

        if field_names:
            specific_field_tuples = [name.split('.') for name in field_names if '.' in name] # tuples of (analysis, field)
            nonspecific_field_names = [name for name in field_names if '.' not in name]

            selected_fields = []    # list of tuples of (analysis_name, field_name)

            for analysis in selected_analyses:
                found = [(field, analysis) for field in analysis.fields() if field.name in nonspecific_field_names]
                selected_fields.extend(found)

            for analysis_name, field_name in specific_field_tuples:
                analysis = model.get_analysis(analysis_name)
                field = analysis.get_field(field_name)
                if field is None:
                    raise CommandlineError(f"Field '{field_name}' was not found in analysis '{analysis_name}'")

                selected_fields.append((field, analysis))

            if not selected_fields:
                raise CommandlineError("The model contains no fields matching command line arguments.")
        else:
            # run all fields for selected analyses
            selected_fields = [(field, analysis) for analysis in selected_analyses for field in analysis.fields()]

        errors = []  # accumulate these to print again at the end

        for field, analysis in selected_fields:
            try:
                field.run(analysis)
                field.report()
            except OpgeeException as e:
                if args.ignore_errors:
                    _logger.error(f"Error in {field}: {e}")
                    errors.append((field, e))
                else:
                    raise

        # TBD: save errors to a file
        if errors:
            print("\nErrors:")

            for field, e in errors:
                print(f"{field}: {e}")

        if args.output:
            model.save_results(selected_fields, args.output)

        if args.by_process:
            model.save_results(selected_fields, args.by_process, by_process=True)

        if args.save_comparison:
            model.save_for_comparison(selected_fields, args.save_comparison)
