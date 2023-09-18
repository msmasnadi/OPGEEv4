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


    #
    # TBD: This was part of the old run() method, kept here for reference for now
    #
    # def remainder_of_run(self):
    #
    #     # TBD: read analysis names without instantiating entire model
    #     #  by calling model_file.model_analysis_names(model_xml_pathname)
    #     #  Then get field name with fields_for_analysis(model_xml, analysis_name)
    #     #  Avoid reading model here; push this into run_serial / run_parallel
    #     mf = ModelFile(model_files, use_default_model=use_default_model,
    #                    analysis_names=analysis_names, field_names=field_names)
    #     model = mf.model
    #
    #     all_analyses = model.analyses()
    #     if analysis_names:
    #         selected_analyses = [ana for ana in all_analyses if ana.name in analysis_names]
    #         if not selected_analyses:
    #             raise CommandlineError(f"Specified analyses {analysis_names} were not found in model")
    #     else:
    #         selected_analyses = list(all_analyses)
    #
    #     if field_names:
    #         specific_field_tuples = [name.split('.') for name in field_names if '.' in name] # tuples of (analysis, field)
    #         nonspecific_field_names = [name for name in field_names if '.' not in name]
    #
    #         selected_fields = []    # list of tuples of (analysis_name, field_name)
    #
    #         for analysis in selected_analyses:
    #             found = [(field, analysis) for field in analysis.fields() if field.name in nonspecific_field_names]
    #             selected_fields.extend(found)
    #
    #         # TBD: convert this to use run_parallel or run_serial
    #         for analysis_name, field_name in specific_field_tuples:
    #             analysis = model.get_analysis(analysis_name)
    #             field = analysis.get_field(field_name)
    #             if field is None:
    #                 raise CommandlineError(f"Field '{field_name}' was not found in analysis '{analysis_name}'")
    #
    #             selected_fields.append((field, analysis))
    #
    #         if not selected_fields:
    #             raise CommandlineError("The model contains no fields matching command line arguments.")
    #     else:
    #         # run all fields for selected analyses
    #         selected_fields = [(field, analysis) for analysis in selected_analyses for field in analysis.fields()]
    #
    #     errors = []  # accumulate these to print again at the end
    #     results = []
    #
    #     # TBD: turn these into a packet for consistency and to share
    #     #  result processing / saving logic
    #     for field, analysis in selected_fields:
    #         try:
    #             field.run(analysis)
    #             result = field.get_result(analysis, result_type, collect)
    #             results.append(result)
    #         except OpgeeException as e:
    #             if args.ignore_errors:
    #                 _logger.error(f"Error in {field}: {e}")
    #                 errors.append((field, e))
    #             else:
    #                 raise
    #
    #     save_results(results, result_type)

    # Deprecated. This was the run() method from the runsim plugin.
    # def runsim(self, args):
    #     from ..error import OpgeeException
    #     from ..utils import parseTrialString
    #     from ..manager import Manager, save_results, TrialPacket
    #     from ..mcs.simulation import Simulation
    #
    #     sim_dir = args.simulation_dir
    #     field_names = args.fields or []
    #     num_fields = args.num_fields
    #     num_tasks = args.num_tasks
    #     result_type = args.result_type
    #     trials = args.trials
    #     collect = args.collect
    #
    #     if sim_dir and not field_names:
    #         metadata = Simulation.read_metadata(sim_dir)
    #         field_names = metadata['field_names']
    #
    #     if not (num_tasks or num_fields or field_names):
    #         raise OpgeeException(f"Must specify field names (-f/--fields), number of fields "
    #                              f"(-N/--num-fields) or number of tasks (-n/--num_tasks)")
    #
    #     if num_fields:
    #         field_names = field_names[:num_fields]
    #
    #     trial_nums = metadata['trials'] if trials == 'all' else parseTrialString(trials)
    #
    #     if num_tasks is None:
    #         num_tasks = len(field_names)
    #
    #     # TBD: could generate FieldPackets or TrialPackets based on args to packetize()
    #     #  then this method could be used for either type of parallelism.
    #     #  Need to compare with run_many.
    #     packets = TrialPacket.packetize(sim_dir, field_names, trial_nums, args.packet_size)
    #
    #     # TBD: once packets are generated, MCS should share cluster / results saving
    #     #  logic with run_many.
    #
    #     mgr = Manager(cluster_type=args.cluster_type)
    #
    #     # Put the log for the Manager process in the simulation directory.
    #     # Each Worker will set the log file to within the directory for
    #     # the field it's currently running.
    #     setLogFile(f"{sim_dir}/opgee-mcs.log", remove_old_file=True)
    #
    #     # TBD: convert run_packets() to yield packet results one at a time
    #     #  Then save each here, respecting batch saving arguments.
    #     results = mgr.run_packets(packets,
    #                               result_type=result_type,
    #                               num_engines=num_tasks,
    #                               minutes_per_task=args.minutes)
    #
    #     save_results(results, result_type)
    #
    #     if collect:
    #         # collect partial result files
    #         pass
    #
    # # Deprecated; kept here for reference
    # # TBD: needs to be modified to use packets and be called from run command
    # #  Or perhaps to replace most of the code in the run command
    # def run_many(self,
    #     model_xml_file,
    #     analysis_name,
    #     field_names,
    #     output,
    #     count=0,
    #     start_with=0,
    #     save_after=None,
    #     skip_fields=None,
    #     batch_start=0,
    #     parallel=True,
    # ):
    #     import os
    #     import pandas as pd
    #     from ..config import getParam, setParam, pathjoin
    #     from ..error import CommandlineError
    #     from ..manager import run_serial, run_parallel
    #     from ..model_file import model_analysis_names, fields_for_analysis
    #
    #     # TBD: unclear if this is necessary
    #     setParam("OPGEE.XmlSavePathname", "")  # avoid writing /tmp/final.xml since no need
    #
    #     analysis_name = analysis_name or model_analysis_names(model_xml_file)[0]
    #     all_fields = fields_for_analysis(model_xml_file, analysis_name)
    #
    #     field_names = [name.strip() for name in field_names] if field_names else None
    #     if field_names:
    #         unknown = set(field_names) - set(all_fields)
    #         if unknown:
    #             raise CommandlineError(f"Fields not found in {model_xml_file}: {unknown}")
    #     else:
    #         field_names = all_fields
    #
    #     if start_with:
    #         # skip all before the named field
    #         i = field_names.index(start_with)
    #         field_names = field_names[i:]
    #
    #     if count:
    #         field_names = field_names[:count]
    #
    #     if skip_fields:
    #         field_names = [name.strip() for name in field_names if name not in skip_fields]
    #
    #     # TBD: replace these with a save function that takes a list of FieldResults
    #     def _save_cols(columns, csvpath):
    #         df = pd.concat(columns, axis="columns")
    #         df.index.name = "process"
    #         df.sort_index(axis="rows", inplace=True)
    #
    #         print(f"Writing '{csvpath}'")
    #         df.to_csv(csvpath)
    #
    #     def _save_errors(errors, csvpath):
    #         """Save a description of all field run errors"""
    #         with open(csvpath, "w") as f:
    #             f.write("analysis,field,error\n")
    #             for result in errors:
    #                 f.write(f"{result.analysis_name},{result.field_name},{result.error}\n")
    #
    #     temp_dir = getParam("OPGEE.TempDir")
    #     dir_name, filename = os.path.split(
    #         output
    #     )  # TBD: output should be a directory since ext must be CSV.
    #     subdir = pathjoin(temp_dir, dir_name)
    #     basename, ext = os.path.splitext(filename)
    #
    #     if save_after:
    #         batch = batch_start  # used in naming result files
    #
    #         # TBD: instead of max_results, use packets which should collapse these two main branches
    #         for results in run_parallel(
    #             model_xml_file, analysis_name, field_names, max_results=save_after
    #         ):
    #
    #             energy_cols = [r.energy for r in results if r.error is None]
    #             emissions_cols = [r.emissions for r in results if r.error is None]
    #             errors = [r.error for r in results if r.error is not None]
    #
    #             # TBD: save CI results
    #             # _save_cols(energy_cols, pathjoin(subdir, f"{basename}-CI{ext}"))
    #
    #             _save_cols(energy_cols, pathjoin(subdir, f"{basename}-energy-{batch}{ext}"))
    #             _save_cols(
    #                 emissions_cols, pathjoin(subdir, f"{basename}-emissions-{batch}{ext}")
    #             )
    #             _save_errors(errors, pathjoin(subdir, f"{basename}-errors-{batch}.csv"))
    #
    #             batch += 1
    #
    #     else:
    #         # If not running in batches, save all results at the end
    #         run_func = run_parallel if parallel else run_serial
    #         results = run_func(
    #             model_xml_file, analysis_name, field_names, max_results=save_after
    #         )
    #
    #         energy_cols = [r.energy for r in results if r.error is None]
    #         emissions_cols = [r.emissions for r in results if r.error is None]
    #         errors = [r.error for r in results if r.error is not None]
    #
    #         # TBD: save CI results
    #         # _save_cols(energy_cols, pathjoin(subdir, f"{basename}-CI{ext}"))
    #
    #         # Insert "-energy" or "-emissions" between basename and extension
    #         _save_cols(energy_cols, pathjoin(subdir, f"{basename}-energy{ext}"))
    #         _save_cols(emissions_cols, pathjoin(subdir, f"{basename}-emissions{ext}"))
    #         _save_errors(errors, pathjoin(subdir, f"{basename}-errors.csv"))
