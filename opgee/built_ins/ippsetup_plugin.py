# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
import os
from ..subcommand import SubcommandABC, clean_help
from ..error import CommandlineError
from ..log import getLogger

_logger = getLogger(__name__)

#
# Changes to make to boilerplate ipython parallel config files. Lines are added
# to the end of the file after performing substitutions on "{variables}".
#
FileChanges = {
    'ipcluster_config.py': """
#
# Added by opg ippsetup
#
c.IPClusterEngines.engine_launcher_class = '{scheduler}'
c.IPClusterEngines.n = {engines}
c.IPClusterStart.delay = 0.1
c.SlurmLauncher.account = '{account}'
c.SlurmEngineSetLauncher.account = '{account}'
c.SlurmControllerLauncher.batch_template_file = 'slurm_controller.template'
c.SlurmEngineSetLauncher.batch_template_file = 'slurm_engine.template'
""",

    'ipengine_config.py': """
#
# Added by opg ippsetup
#

# See https://gist.github.com/basnijholt/c375ea2d1df6702492b619e0873d6c7c
c.IPEngineApp.wait_for_url_file = 300
c.IPEngine.timeout = 300
""",

    'ipcontroller_config.py': """
#
# Added by opg ippsetup
#

# See https://gist.github.com/basnijholt/c375ea2d1df6702492b619e0873d6c7c
c.HubFactory.registration_timeout = 600
c.HubFactory.client_ip = '*'
c.HubFactory.engine_ip = '*'
"""
}

class IppSetupCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Start an ipyparallel cluster after generating batch
        file templates based on parameters in opgee.cfg and the number of tasks to run.'''}
        super(IppSetupCommand, self).__init__('ippsetup', subparsers, kwargs)

    def addArgs(self, parser):
        from ..config import getParam
        from os import cpu_count

        defaultAccount = getParam('SLURM.Account')
        defaultProfile = getParam('IPP.Profile')
        defaultEngines = cpu_count()
        # schedulers = ('Slurm', 'PBS', 'LSF')
        # defaultScheduler = schedulers[0]

        parser.add_argument('-a', '--account', default=defaultAccount,
                            help=f'''The account name to use to run jobs on the cluster system.
                            Used by Slurm only. Default is the value of config variable
                            "SLURM.Account", currently "{defaultAccount}"''')

        parser.add_argument('-e', '--engines', type=int, default=defaultEngines,
                            help=f'''Set default number of engines to allow per node. Note that
                            this is overridden by runsim; this value given here will be used 
                            only when running the cluster "manually". The default value is the
                            number of CPUs detected by os.cpu_count(), currently {defaultEngines}''')

        parser.add_argument('-p', '--profile', type=str, default=defaultProfile,
                            help=f'''The name of the ipython profile to create. Default is the
                            value of config parameter IPP.Profile, currently "{defaultProfile}".''')

        parser.add_argument('--overwrite', action="store_true",
                            help='''Remove and recreate the specified IPP profile directory.''')

        # parser.add_argument('-s', '--scheduler', choices=schedulers, default=defaultScheduler,
        #                     help=clean_help('''The resource manager / scheduler your system uses.
        #                     Default is %s.''' % defaultScheduler))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from IPython.paths import get_ipython_dir
        import subprocess as subp
        from ..utils import filecopy, removeTree

        formatDict = {
            'scheduler': 'Slurm',       # support only SLURM for now
            'account': args.account,
            'engines'  : args.engines,
        }

        profile = args.profile

        ipythonDir = get_ipython_dir()
        profileDir = os.path.join(ipythonDir, 'profile_' + profile)

        if args.overwrite:
            removeTree(profileDir)

        if os.path.isdir(profileDir):
            raise CommandlineError(f'Ipython profile directory "{profileDir}" already exists. '
                                   f'Delete it, choose another name, or use "opg ippsetup --overwrite".')

        cmd = f"ipython profile create '{profile}' --parallel"
        _logger.info('Running command: %s', cmd)
        subp.call(cmd, shell=True)

        for basename, lines in FileChanges.items():
            pathname = os.path.join(profileDir, basename)
            backup   = pathname + '~'

            if not os.path.isfile(pathname):
                raise CommandlineError(f'Missing configuration file: "{pathname}"')

            _logger.info(f'Editing config file: "{pathname}"')
            filecopy(pathname, backup)

            with open(pathname, 'a') as output:
                lines = lines.format(**formatDict)
                output.write(lines)
