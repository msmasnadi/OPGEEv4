from ..subcommand import SubcommandABC #, clean_help

# TBD: get these from the command line
DFLT_MODEL_FILE = '/Users/rjp/repos/OPGEEv4/tests/files/test_separator.xml'
DFLT_FIELD = 'test'
DFLT_ANALYSIS = 'test_separator'


class GUICommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Run the OPGEE Graphical User Interface'''}

        super(GUICommand, self).__init__('gui', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('-d', '--debug', action='store_true',
                            help='''Enable debug mode in the dash server''')

        parser.add_argument('-H', '--host', default='127.0.0.1',
                            help='''Set the host address to serve the application on. Default is localhost (127.0.0.1).''')

        parser.add_argument('-P', '--port', default=8050, type=int,
                            help='''Set the port to serve the application on. Default is 8050.''')

        parser.add_argument('-a', '--analysis', default=DFLT_ANALYSIS,
                            help=f'''The analysis to run. Default (for testing) is "{DFLT_ANALYSIS}"''')

        parser.add_argument('-f', '--field', default=DFLT_FIELD,
                            help=f'''The field to display. Default (for testing) is "{DFLT_FIELD}"''')

        # TBD: If not provided, use path found in opgee.cfg
        parser.add_argument('-m', '--modelFile', default=DFLT_MODEL_FILE,
                            help=f'''The OPGEE model XML file to read. Default (for testing) is "{DFLT_MODEL_FILE}"''')

        # TBD: apparently action=argparse.BooleanOptionalAction requires py 3.9
        parser.add_argument('--add-stream-components', action='store_true',
                            help=f'''Whether to include additional stream components, if found in opgee.cfg''')

        parser.add_argument('--use-class-path', action='store_true',
                            help=f'''Whether to use the config variable CLASSPATH to find custom Process subclasses''')

        return parser

    def run(self, args, tool):
        from ..gui.app import main
        main(args)

PluginClass = GUICommand
