from ..subcommand import SubcommandABC #, clean_help

DFLT_FIELD = 'test'
DFLT_ANALYSIS = 'test'


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

        parser.add_argument('-m', '--modelFile', default=None,
                            help=f'''The OPGEE model XML file to read. Default is the value of config variable 'OPGEE.ModelFile', 
                                     if defined, otherwise the built-in opgee.xml.''')

        # TBD: apparently action=argparse.BooleanOptionalAction requires py 3.9
        parser.add_argument('--add-stream-components', action='store_true',
                            help=f'''Include additional stream components listed in config variable "OPGEE.StreamComponents"''')

        parser.add_argument('--use-class-path', action='store_true',
                            help=f'''Search for Process subclasses in Python files found in the path(s) listed in config variable "OPGEE.ClassPath"''')

        return parser

    def run(self, args, tool):
        from ..gui.app import main
        main(args)

PluginClass = GUICommand
