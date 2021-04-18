'''
.. The "opg" commandline program

.. Adapted from tool.py in pygcam.
   Added to opgee on 3/29/21.

.. Copyright (c) 2016-2021 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''

import argparse
from glob import glob
import os
import sys
from .config import (pathjoin, getParam, getConfig, getParamAsBoolean, getParamAsFloat,
                     setParam, getSection, setSection, getSections)
from .error import OpgeeException, CommandlineError
from .log import getLogger, setLogLevels, configureLogs
from .signals import SignalException, catchSignals
from .subcommand import clean_help
from .version import VERSION
from .windows import IsWindows

PROGRAM = 'opg'

# For now, these are not offered as command-line options. Needs more testing.
# BioConstraintsCommand, DeltaConstraintsCommand,

class Opgee(object):

    # plugin instances by command name
    _plugins = {}

    # cached plugin paths by command name
    _pluginPaths = {}

    @classmethod
    def getPlugin(cls, name):
        if name not in cls._plugins:
            cls._loadCachedPlugin(name)

        return cls._plugins.get(name, None)

    @classmethod
    def _loadCachedPlugin(cls, name):
        # see if it's already loaded
        path = cls._pluginPaths[name]
        tool = cls.getInstance()
        tool.loadPlugin(path)

    @classmethod
    def _cachePlugins(cls):
        '''
        Find all plugins via OPGEE.PluginPath and create a dict
        of plugin pathnames keyed by command name so the plugin
        can be loaded on-demand.
        :return: none
        '''
        pluginDirs = cls._getPluginDirs()

        suffix = '_plugin.py'
        suffixLen = len(suffix)

        for d in pluginDirs:
            pattern = pathjoin(d, '*' + suffix)
            for path in glob(pattern):
                basename = os.path.basename(path)
                command = basename[:-suffixLen]
                cls._pluginPaths[command] = path

    _instance = None

    @classmethod
    def getInstance(cls, loadPlugins=True, reload=False):
        """
        Get the singleton instance of the Opgee class.

        :param loadPlugins: (bool) If true, plugins are loaded (only
           when first allocated).
        :param reload: (bool) If true, a new Opgee instance is
           created.
        :return: (Opgee instance) the new or cached instance.
        """
        if reload:
            Opgee._instance = None
            Opgee._plugins = {}
            Opgee._pluginPaths = {}

        if not Opgee._instance:
            Opgee._instance = cls(loadPlugins=loadPlugins)

        return Opgee._instance

    @classmethod
    def pluginGroup(cls, groupName, namesOnly=False):
        objs = filter(lambda obj: obj.getGroup() == groupName, cls._plugins.values())
        result = sorted(map(lambda obj: obj.name, objs)) if namesOnly else list(objs)
        return result

    def __init__(self, loadPlugins=True, loadBuiltins=True):
        self.shellArgs = None

        self.parser = self.subparsers = None
        self.addParsers()

        # load all built-in sub-commands
        if loadBuiltins:
            from .built_ins import BuiltinSubcommands
            for item in BuiltinSubcommands:
                self.instantiatePlugin(item)

        # Load external plug-ins found in plug-in path
        if loadPlugins:
            self._cachePlugins()

    def addParsers(self):
        self.parser = parser = argparse.ArgumentParser(prog=PROGRAM, prefix_chars='-+')

        parser.add_argument('+b', '--batch', action='store_true',
                            help=clean_help('''Run the commands by submitting a batch job using the command
                            given by config variable OPGEE.BatchCommand. (Linux only)'''))

        parser.add_argument('+B', '--showBatch', action="store_true",
                            help=clean_help("Show the batch command to be run, but don't run it. (Linux only)"))

        parser.add_argument('+D', '--dirmap',
                            help=clean_help("""A comma-delimited sequence of colon-delimited directory names 
                            of the form "/some/host/path:/a/container/path, /host:cont, ...", 
                            mapping host dirs to their mount point in a docker container."""))

        parser.add_argument('+e', '--enviroVars',
                            help=clean_help('''Comma-delimited list of environment variable assignments to pass
                            to queued batch job, e.g., -E "FOO=1,BAR=2". (Linux only)'''))

        parser.add_argument('+j', '--jobName', default='gt',
                            help=clean_help('''Specify a name for the queued batch job. Default is "gt".
                            (Linux only)'''))

        logLevel = str(getParam('OPGEE.LogLevel'))   # so not unicode
        parser.add_argument('+l', '--logLevel',
                            default=logLevel or 'notset',
                            help=clean_help('''Sets the log level for modules of the program. A default
                                log level can be set for the entire program, or individual 
                                modules can have levels set using the syntax 
                                "module:level, module:level,...", where the level names must be
                                one of {debug,info,warning,error,fatal} (case insensitive).'''))

        parser.add_argument('+L', '--logFile',
                            help=clean_help('''Sets the name of a log file for batch runs. Default is "gt-%%j.out"
                            where "%%j" (in SLURM) is the jobid. If the argument is not an absolute
                            pathname, it is treated as relative to the value of OPGEE.LogDir.'''))

        parser.add_argument('+m', '--minutes', type=float, default=getParamAsFloat('OPGEE.Minutes'),
                            help=clean_help('''Set the number of minutes to allocate for the queued batch job.
                            Overrides config parameter OPGEE.Minutes. (Linux only)'''))

        parser.add_argument('+P', '--projectName', metavar='name', default=getParam('OPGEE.DefaultProject'),
                            choices=sorted(getSections()),
                            help=clean_help('''The project name (the config file section to read from),
                            which defaults to the value of config variable OPGEE.DefaultProject'''))

        parser.add_argument('+q', '--queueName', default=getParam('OPGEE.DefaultQueue'),
                            help=clean_help('''Specify the name of the queue to which to submit the batch job.
                            Default is given by config variable OPGEE.DefaultQueue. (Linux only)'''))

        parser.add_argument('+r', '--resources', default='',
                            help=clean_help('''Specify resources for the queued batch command. Can be a comma-delimited
                            list of assignments of the form NAME=value, e.g., -r 'pvmem=6GB'. (Linux only)'''))

        parser.add_argument('+s', '--set', dest='configVars', metavar='name=value', action='append', default=[],
                            help=clean_help('''Assign a value to override a configuration file parameter. For example,
                            to set batch commands to start after a prior job of the same name completes,
                            use --set "OPGEE.OtherBatchArgs=-d singleton". Enclose the argument in quotes if
                            it contains spaces or other characters that would confuse the shell.
                            Use multiple --set flags and arguments to set multiple variables.'''))

        parser.add_argument('+v', '--verbose', action='store_true',
                            help=clean_help('''Show diagnostic output'''))

        parser.add_argument('--version', action='version', version=VERSION)   # goes to stderr, handled by argparse

        parser.add_argument('--VERSION', action='store_true')   # goes to stdout, but handled by gt

        self.subparsers = self.parser.add_subparsers(dest='subcommand', title='Subcommands',
                               description='''For help on subcommands, use the "-h" flag after the subcommand name''')


    def instantiatePlugin(self, pluginClass):
        plugin = pluginClass(self.subparsers)
        self._plugins[plugin.name] = plugin

    @staticmethod
    def _getPluginDirs():
        pluginPath = getParam('OPGEE.PluginPath')
        if not pluginPath:
            return []

        sep = os.path.pathsep           # ';' on Windows, ':' on Unix
        items = pluginPath.split(sep)

        return items

    def loadPlugin(self, path):
        """
        Load the plugin at `path`.

        :param path: (str) the pathname of a plugin file.
        :return: an instance of the ``SubcommandABC`` subclass defined in `path`
        """
        from .utils import loadModuleFromPath

        def getModObj(mod, name):
            return getattr(mod, name) if name in mod.__dict__ else None

        mod = loadModuleFromPath(path)

        pluginClass = getModObj(mod, 'PluginClass') or getModObj(mod, 'Plugin')
        if not pluginClass:
            raise OpgeeException(f'Neither PluginClass nor class Plugin are defined in {path}')

        self.instantiatePlugin(pluginClass)

    def _loadRequiredPlugins(self, argv):
        # Create a dummy subparser to allow us to identify the requested
        # sub-command so we can load the module if necessary.
        parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False, prefix_chars='-+')
        parser.add_argument('-h', '--help', action='store_true')
        parser.add_argument('+P', '--projectName', metavar='name')

        ns, otherArgs = parser.parse_known_args(args=argv)

        # For top-level help, or if no args, load all plugins
        # so the generated help messages includes all subcommands
        if ns.help or not otherArgs:
            for item in self._pluginPaths.keys():
                self._loadCachedPlugin(item)
        else:
            # Otherwise, load any referenced sub-command
            for command in self._pluginPaths.keys():
                if command in otherArgs:
                    self.getPlugin(command)

    def run(self, args=None, argList=None):
        """
        Parse the script's arguments and invoke the run() method of the
        designated sub-command.

        :param args: an argparse.Namespace of parsed arguments
        :param argList: (list of str) argument list to parse (when called recursively)
        :return: none
        """
        assert args or argList, "Opgee.run() requires either args or argList"

        # checkWindowsSymlinks() # not needed for opgee

        if argList is not None:         # might be called with empty list of subcmd args
            # called recursively
            self._loadRequiredPlugins(argList)
            args = self.parser.parse_args(args=argList)

        else:  # top-level call
            if args.batch:
                args.batch = False

            args.projectName = section = args.projectName or getParam('OPGEE.DefaultProject')
            if section:
                 setSection(section)

            logLevel = args.logLevel or getParam('OPGEE.LogLevel')
            if logLevel:
                setLogLevels(logLevel)

            configureLogs(force=True)

        # Get the sub-command and run it with the given args
        obj = self.getPlugin(args.subcommand)

        obj.run(args, self)

def _getMainParser():
    '''
    Used only to generate documentation by sphinx' argparse, in which case
    we don't generate documentation for project-specific plugins.
    '''
    getConfig(allowMissing=True)
    tool = Opgee.getInstance(loadPlugins=False)
    return tool.parser


def checkWindowsSymlinks():
    '''
    If running on Windows and OPGEE.CopyAllFiles is not set, and
    we fail to create a test symlink, set OPGEE.CopyAllFiles to True.
    '''
    from .temp_file import getTempFile

    if IsWindows and not getParamAsBoolean('OPGEE.CopyAllFiles'):
        src = getTempFile()
        dst = getTempFile()

        try:
            os.symlink(src, dst)
        except:
            _logger = getLogger(__name__)
            _logger.info('No symlink permission; setting OPGEE.CopyAllFiles = True')
            setParam('OPGEE.CopyAllFiles', 'True')

# This parser handles only --VERSION flag.
def _showVersion(argv):
    parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False, prefix_chars='-+')
    parser.add_argument('--VERSION', action='store_true')

    ns, otherArgs = parser.parse_known_args(args=argv)

    if ns.VERSION:
        print(VERSION)
        sys.exit(0)

def _main(argv=None):
    from .config import userConfigPath

    configPath = userConfigPath()
    if not os.path.lexists(configPath) or os.stat(configPath).st_size == 0:
        argSet = set(argv or sys.argv)
        options = {'init', '-h', '--help', '--version'}
        if argSet.intersection(options):
            # create empty config file just so we can run the "init" sub-command, or help/version options
            open(configPath, 'w').close()
        else:
            raise CommandlineError(f'\n***\n*** Missing or empty opgee configuration file {configPath}.\n***\n')

    getConfig()

    _showVersion(argv)
    configureLogs()

    tool = Opgee.getInstance()
    tool._loadRequiredPlugins(argv)

    # This parser handles only --batch, --showBatch, --projectName, and --set
    # args. If --batch is given, we need to create a script and call the
    # OPGEE.BatchCommand on it. We grab --projectName so we can set PluginPath by project.
    parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False, prefix_chars='-+')

    parser.add_argument('+b', '--batch', action='store_true')
    parser.add_argument('+B', '--showBatch', action="store_true")
    parser.add_argument('+P', '--projectName', dest='projectName', metavar='name')
    parser.add_argument('+s', '--set', dest='configVars', action='append', default=[])

    ns, otherArgs = parser.parse_known_args(args=argv)

    # Set specified config vars
    for arg in ns.configVars:
        if not '=' in arg:
            raise CommandlineError(f'+s requires an argument of the form variable=value, got "{arg}"')

        name, value = arg.split('=')
        setParam(name, value)

    # showBatch => don't run batch command, but implies --batch
    if ns.showBatch:
        ns.batch = True

    # Catch signals to allow cleanup of TempFile instances, e.g., on ^C
    catchSignals()

    if ns.batch:
        run = not ns.showBatch
        if ns.projectName:        # add these back in for the batch script
            otherArgs = ['+P', ns.projectName] + otherArgs

        tool.runBatch(otherArgs, run=run)
    else:
        tool.shellArgs = otherArgs  # save for project run method to use in "distribute" mode
        args = tool.parser.parse_args(args=otherArgs)
        tool.run(args=args)


def main(argv=None, raiseError=False):
    try:
        _main(argv)
        return 0

    except CommandlineError as e:
        print(e)

    except SignalException as e:
        if raiseError:
            raise

        _logger = getLogger(__name__)
        _logger.error(f"{PROGRAM}: {e}")
        return e.signum

    except Exception as e:
        if raiseError:
            raise

        print("{PROGRAM} failed: {e}")

        if not getSection() or getParamAsBoolean('OPGEE.ShowStackTrace'):
            import traceback
            traceback.print_exc()

    finally:
        from .temp_file import TempFile

        # Delete any temporary files that were created
        TempFile.deleteAll()

    return 1
