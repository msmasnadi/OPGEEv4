"""
.. OPGEE "run" sub-command

.. Copyright (c) 2021 Richard Plevin and Stanford University
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..subcommand import SubcommandABC
from ..log import getLogger, setLogFile

_logger = getLogger(__name__)


class RunCommand(SubcommandABC):
    def __init__(self, subparsers, name='run', help='Run the specified portion of an OPGEE LCA model'):
        kwargs = {'help' : help}
        super(RunCommand, self).__init__(name, subparsers, kwargs)

    def addArgs(self, parser):
        from ..config import getParam, getParamAsInt
        from ..constants import (CLUSTER_NONE, CLUSTER_TYPES, DEFAULT_RESULT_TYPE,
                                 SIMPLE_RESULT, DETAILED_RESULT, USER_RESULT_TYPES)
        from ..utils import ParseCommaList, positive_int

        partition = getParam('SLURM.Partition')
        min_per_task = getParam('SLURM.MinutesPerTask')
        packet_size = getParamAsInt('OPGEE.MaxTrialsPerPacket')

        # User can specify fields by name, or the number of fields to run MCS for, but not both.
        group = parser.add_mutually_exclusive_group()

        parser.add_argument('-a', '--analyses', action=ParseCommaList,
                            help='''Run only the specified analysis or analyses. Argument may be a 
                            comma-delimited list of Analysis names.''')

        parser.add_argument('-b', '--batch-size', type=int,
                            help='''Write a results to a new file after the results for the given 
                            number of packets are returned. If not specified, results are written 
                            out only after all trials have completed.''')

        parser.add_argument('-B', '--batch-start', default=0, type=int,
                            help='''The value to use to start numbering batch result files.
                            Default is zero. Ignored unless -S/--save-after is also specified.''')

        cluster_type = getParam('OPGEE.ClusterType') or CLUSTER_NONE
        parser.add_argument('-c', '--cluster-type', choices=CLUSTER_TYPES,
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

        parser.add_argument('-F', '--skip-fields', action=ParseCommaList,
                            help='''Comma-delimited list of field names to exclude from analysis''')

        parser.add_argument('-i', '--ignore-errors', action='store_true',
                            help='''Keep running even if some fields raise errors when run''')

        parser.add_argument('-m', '--model-file', action='append',
                            help='''XML model definition files to load. If --no_default_model is not 
                                specified, the built-in files etc/opgee.xml and etc/attributes.xml are 
                                loaded first, and the XML files specified here will be merged with these.
                                If --no_default_model is specified, only the given files are loaded;
                                they are merged in the order stated.''')

        parser.add_argument('-M', '--minutes', default=min_per_task, type=positive_int,
                            help=f'''The amount of wall time to allocate for each task.
                             Default is {min_per_task} minutes. Acceptable time formats include "minutes", 
                             "minutes:seconds", "hours:minutes:seconds", and formats involving days, 
                             which we shouldn't require. Ignored if --cluster-type=slurm is not specified.''')

        parser.add_argument('-n', '--no-default-model', action='store_true',
                            help='''Don't load the built-in opgee.xml model definition.''')

        group.add_argument('-N', "--num-fields", type=positive_int, default=None,
                           help='''Run MCS simulations on the first "num-fields" only.
                            (Mutually exclusive with -f/--fields.)''')

        parser.add_argument('-o', '--output-dir',
                            help='''Write output to the specified directory.''')

        parser.add_argument('-p', "--partition", default=None,
                            help=f'''The name of the partition to use for job submissions. Default is the
                                value of config variable "SLURM.Partition", currently '{partition}'.
                                Ignored if --cluster-type=slurm is not specified.''')

        parser.add_argument('-P', '--packet-size', type=positive_int, default=packet_size,
                            help=f'''Divide runs for a single field into groups of this size
                            to run serially on a single worker. Default is the value of configuration 
                            file parameter "OPGEE.MaxTrialsPerPacket", currently {packet_size}.'''),

        parser.add_argument('-r', '--result-type', type=str, choices=USER_RESULT_TYPES,
                            help=f'''The type of result to return from each field. Default is "{DEFAULT_RESULT_TYPE}".
                            For "{SIMPLE_RESULT}" results, the following values are saved per trial in a separate 
                            file for each field: trial_num, CI, total GHGs, and emissions from combustion, land use,
                            venting/flaring, other. For "{DETAILED_RESULT}" results, per-process emissions and energy
                            use are stored.''')

        parser.add_argument('-s', '--simulation-dir',
                            help='''The top-level directory to use for this simulation "package"''')

        parser.add_argument('-S', '--start-with',
                            help='''The name of a field to start with. Use this to resume a run after a failure.
                            Can be combined with -n/--num-fields to run a large number of fields in smaller batches.''')

        parser.add_argument('-t', '--trials', default='all',
                            help='''The trials to run. Can be expressed as a string containing
                            comma-delimited ranges and individual trail numbers, e.g. "1-20,22, 35, 42, 44-50").
                            The special string "all" (the default) runs all defined trials. Ignored 
                            unless -s/--simulation-dir is specified.''')

        parser.add_argument('-T', "--num-tasks", type=positive_int, default=None,
                            help='''Number of worker tasks to create. Default is the number of fields, if
                                specified using -f/--fields, otherwise -n/--num_tasks is required.''')

        parser.add_argument('-v', '--save-comparison',
                            help='''The name of a CSV file to which to save results suitable for 
                                use with the "compare" subcommand.''')

        return parser

    def run(self, args, tool):
        from ..config import setParam
        from ..error import CommandlineError
        from ..model_file import model_analysis_names, fields_for_analysis
        from ..manager import Manager, save_results, TrialPacket, FieldPacket
        from ..utils import parseTrialString, mkdirs
        from ..mcs.simulation import Simulation, model_file_path

        analysis_names = args.analyses or []
        batch_size = args.batch_size
        batch_start = args.batch_start
        collect = args.collect
        field_names = args.fields or []
        minutes_per_task = args.minutes
        model_files = args.model_file       # all specified model files
        model_xml_file = model_files[0] if model_files else None    # TBD: currently using only the first model file specified
        num_fields = args.num_fields
        num_tasks = args.num_tasks
        output_dir = args.output_dir
        packet_size = args.packet_size
        result_type = args.result_type
        sim_dir = args.simulation_dir
        skip_fields = args.skip_fields
        start_with = args.start_with
        trial_nums = None
        trials = args.trials
        use_default_model = not args.no_default_model

        # TBD: conceptual problem: XML model merging doesn't happen until after we look for
        #  analyses and fields in the model XML. Might want to do XML-level merging before
        #  constructing internal model structure and before expanding templates. That is,
        #  just merge the XML files first, then expand only when about to run the model?
        #  Or when caching it.

        if sim_dir:
            metadata = Simulation.read_metadata(sim_dir)
            field_names = field_names or metadata['field_names']
            trial_nums = metadata["trials"] if trials == "all" else parseTrialString(trials)
            model_xml_file = model_xml_file or model_file_path(sim_dir)

            output_dir = f"{sim_dir}/results"
            mkdirs(output_dir)

            # if not (num_tasks or num_fields or field_names):
            #     raise OpgeeException(
            #         f"Must specify field names (-f/--fields), number of fields "
            #         f"(-N/--num-fields) or number of tasks (-n/--num_tasks)"
            #     )

        if not output_dir:
            raise CommandlineError("Non-MCS runs must specify -o/--output-dir")

        if not (field_names or analysis_names):
            raise CommandlineError("Must indicate one or more fields or analyses to run")

        if not (use_default_model or model_files):
            raise CommandlineError("No model to run: the --model-file option was not used and --no-default-model was specified.")

        # TBD: unclear if this is necessary
        setParam("OPGEE.XmlSavePathname", "")  # avoid writing /tmp/final.xml since no need

        # TBD: decide if we need to support multiple analysis names (only 1st is used currently)
        analysis_name = analysis_names[0] if analysis_names else model_analysis_names(model_xml_file)[0]
        all_fields = fields_for_analysis(model_xml_file, analysis_name)

        field_names = [name.strip() for name in field_names] if field_names else None
        if field_names:
            unknown = set(field_names) - set(all_fields)
            if unknown:
                raise CommandlineError(f"Fields not found in {model_xml_file}: {unknown}")
        else:
            field_names = all_fields

        if start_with:
            # skip all before the named field
            i = field_names.index(start_with)
            field_names = field_names[i:]

        if num_fields:
            field_names = field_names[:num_fields]

        if skip_fields:
            field_names = [name.strip() for name in field_names if name not in skip_fields]

        mgr = Manager(cluster_type=args.cluster_type)

        if sim_dir:
            if num_tasks is None:
                num_tasks = len(field_names)

            packets = TrialPacket.packetize(sim_dir, trial_nums, field_names, packet_size)
        else:
            packets = FieldPacket.packetize(model_xml_file, analysis_name,
                                            field_names, packet_size)

        results_list = []
        save_batches = batch_size is not None
        batch_num = batch_start

        for results in mgr.run_packets(packets,
                                      result_type=result_type,
                                      num_engines=num_tasks,
                                      minutes_per_task=minutes_per_task):

            # Save to disk, optionally in batches.
            results_list.append(results)
            if save_batches:
                if len(results_list) >= batch_size:
                    save_results(results_list, output_dir, batch_num=batch_num)
                    results_list.clear()
                    batch_num += 1

        if results_list:
            save_results(results_list, output_dir, batch_num=batch_num if batch_size else None)

        if collect and save_batches:
            # Combine partial result files into one
            pass
