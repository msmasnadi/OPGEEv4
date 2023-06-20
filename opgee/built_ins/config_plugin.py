'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from ..error import OpgeeException, CommandlineError
from ..subcommand import SubcommandABC, clean_help

class ConfigCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''List the values of configuration variables from
                  ~/opgee.cfg configuration file.'''}

        super(ConfigCommand, self).__init__('config', subparsers, kwargs, group='utils')

    def addArgs(self, parser):
        parser.add_argument('-d', '--useDefault', action='store_true',
                            help=clean_help('Indicates to operate on the DEFAULT section rather '
                                 'than the project section.'))

        parser.add_argument('-e', '--edit', action='store_true',
                            help=clean_help('Edit the configuration file. The command given by the '
                            'value of config variable OPGEE.TextEditor is run with the '
                            'opgee.cfg file as an argument.'))

        parser.add_argument('name', nargs='?', default='',
                            help=clean_help('Show the names and values of all parameters whose '
                            'name contains the given value. The match is case-insensitive. '
                            'If not specified, all variable values are shown.'))

        parser.add_argument('-x', '--exact', action='store_true',
                            help=clean_help('Treat the text not as a substring to match, but '
                            'as the name of a specific variable. Match is case-sensitive. '
                            'Prints only the value.'))
        return parser

    def run(self, args, tool):
        import re
        import subprocess
        from ..config import getParam, _ConfigParser, USR_CONFIG_FILE

        if args.edit:
            editor = getParam('OPGEE.TextEditor')
            home = getParam('Home')
            cmd = f"{editor} {home}/{USR_CONFIG_FILE}"
            print(cmd)
            exitStatus = subprocess.call(cmd, shell=True)
            if exitStatus != 0:
                raise OpgeeException(f"TextEditor command '{cmd}' exited with status {exitStatus}\n")
            return

        section = 'DEFAULT' if args.useDefault else args.projectName

        if not section:
            raise CommandlineError("Project was not specified and OPGEE.DefaultProject is not set")

        if section != 'DEFAULT' and not _ConfigParser.has_section(section):
            raise CommandlineError(f"Unknown configuration file section '{section}'")

        if args.name and args.exact:
            value = getParam(args.name, section=section, raiseError=False)
            if value is not None:
                print(value)
            return

        # if no name is given, the pattern matches all variables
        pattern = re.compile('.*' + args.name + '.*', re.IGNORECASE)

        print(f"[{section}]")
        for name, value in sorted(_ConfigParser.items(section)):
            if pattern.match(name):
                # getParam does path translation for docker, if required
                value = getParam(name, section=section, raiseError=False)
                print(f"{name:>25s} = {value}")


PluginClass = ConfigCommand
