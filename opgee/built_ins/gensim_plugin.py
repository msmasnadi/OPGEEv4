'''
.. Created 2016 as part of pygcam.
   Imported into, and simplified for opgee on 06/06/22

.. Copyright (c) 2016-2022 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from ..log import getLogger
from ..subcommand import SubcommandABC

_logger = getLogger(__name__)

class GensimCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : 'Generate simulation directory and trial data for a Monte Carlo simulation.'}
        super(GensimCommand, self).__init__('gensim', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('-a', '--analysis',
                            help='''The name of the analysis for which to generate a simulation''')

        parser.add_argument('-d', '--distributions',
                            help='''The path to a CSV file with distribution definitions. If omitted, the 
                            built-in file etc/parameter_distributions.csv is used.''')

        parser.add_argument('-m', '--model-file', action='append',
                            help='''XML model definition files to load. If --no_default_model is *not* specified,
                            the built-in files etc/opgee.xml and etc/attributes.xml are loaded first, and the XML 
                            files specified here will be merged with these. If --no_default_model is specified, 
                            only the given files are loaded; they are merged in the order stated.''')

        parser.add_argument('-n', '--no-default-model', action='store_true',
                            help='''Don't load the built-in opgee.xml model definition.''')

        parser.add_argument('--overwrite', action='store_true',
                            help='''DELETE and recreate the simulation directory.''')

        parser.add_argument('-s', '--simulation-dir',
                            help='''The top-level directory to create for this simulation "package"''')

        parser.add_argument('-t', '--trials', type=int, default=0,
                            help='''The number of trials to create for this simulation (REQUIRED).''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from ..error import McsUserError, CommandlineError
        from ..mcs.simulation import Simulation, read_distributions, model_file_path

        use_default_model = not args.no_default_model
        model_files = args.model_file

        if args.trials <= 0:
            raise McsUserError("Trials argument must be an integer > 0")

        if not (use_default_model or model_files):
            raise CommandlineError("No model to run: the --model-file option was not used and --no-default-model was specified.")

        read_distributions(pathname=args.distributions)

        sim_dir = args.simulation_dir
        analysis_name = args.analysis

        Simulation.new(sim_dir, model_files, analysis_name, args.trials,
                       overwrite=args.overwrite, use_default_model=use_default_model)
