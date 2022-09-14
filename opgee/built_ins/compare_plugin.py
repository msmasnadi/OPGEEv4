#
# Generate and compare CSV files of process-level results for a set of fields.
# Usually used to compare with similar output from Excel (OPGEEv3) and here (OPGEEv4).
#
from opgee.subcommand import SubcommandABC

class CompareCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Generate and compare result CSV files''',
                  'description' : '''Generates a CSV file with fields in columns and processes in row,
                      with the value either blank for disabled processes, or the total energy use per
                      day by process, after running the model. Mainly used for testing against OPGEEv3.'''}

         super(CompareCommand, self).__init__('compare', subparsers, kwargs)

    def addArgs(self):
        '''
        Process the command-line arguments for this sub-command
        '''
        parser = self.parser

        parser.add_argument('-a', '--analysis',
                            help='''The name of the Analysis containing the fields to run.''')

        parser.add_argument('-b', '--baselineCSV',
                            help='''A file containing baseline results against which we 
                                compare "comparisonCSV"''')

        parser.add_argument('-s', '--saveCSV',
                            help='''Generate per-process results for the indicated fields and save
                                them to the file given by this argument, by running the indicated model.''')

        parser.add_argument('-c', '--comparisonCSV',
                            help='''The pathname of a saved results CSV file to compare to "resultsCSV".''')

        parser.add_argument('-x', '--xml', default=None,
                            help='''The name of the model XML file to use. Default is the built-in
                                "etc/opgee.xml".''')

        parser.add_argument('-n', '--count', type=int, default=0,
                            help='''The number of fields to run in the specified Analysis.
                                Default is 0, which means run all fields in the Analysis.''')
        return parser

    def run(self, args, tool):
        '''
        Implement the sub-command here. "args" is an `argparse.Namespace` instance
        holding the parsed command-line arguments, and "tool" is a reference to
        the running OpgeeTool instance.
        '''
        # from opgee.log import getLogger
        # _logger = getLogger(__name__)

        xml = args.xml or 'etc/opgee.xml' # TBD: open this and pass stream


# An alternative to naming the class 'Plugin' is to assign the class to PluginClass
PluginClass = CompareCommand
