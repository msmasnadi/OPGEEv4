# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
import os
from ..subcommand import SubcommandABC, clean_help
from ..error import CommandlineError
from ..log import getLogger

_logger = getLogger(__name__)

#
# Changes to make to boilerplate ipython parallel config files. Format is
# {filename : ((match, replacement), (match, replacement)), filename: ...}
#
FileChanges = {
    'ipcluster_config.py': (
        ("#\s*c.IPClusterEngines.engine_launcher_class = 'LocalEngineSetLauncher",
         "c.IPClusterEngines.engine_launcher_class = '{scheduler}'"),

        ("#\s*c.IPClusterEngines.n = ",    # not sure if number is constant across platforms...
         "c.IPClusterEngines.n = {engines}"),

        ("#\s*c.IPClusterStart.delay = 1.0",
         "# No need to delay queuing engines with controller on login node\nc.IPClusterStart.delay = 0.1"),

        ("#\s*c.SlurmLauncher.account = ",
         "c.SlurmLauncher.account = '{account}'"),

        ("#\s*c.SlurmEngineSetLauncher.account = ",
         "c.SlurmEngineSetLauncher.account = '{account}'"),

        # ("#\s*c.SlurmLauncher.timelimit = ''",
        #  "c.SlurmLauncher.timelimit = '{walltime}'"),

        ("#\s*c.SlurmControllerLauncher.batch_template_file = ",
         "c.SlurmControllerLauncher.batch_template_file = 'slurm_controller.template'"),

        ("#\s*c.SlurmEngineSetLauncher.batch_template_file = ",
         "c.SlurmEngineSetLauncher.batch_template_file = 'slurm_engine.template'"),
    ),

    'ipcontroller_config.py': (
        ("#\s*c.HubFactory.client_ip\s*=\s*''",
         "c.HubFactory.client_ip = '*'"),

        ("#\s*c.HubFactory.engine_ip\s*=\s*''",
         "c.HubFactory.engine_ip = '*'"),
    )
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
        schedulers = ('Slurm', 'PBS', 'LSF')
        defaultScheduler = schedulers[0]

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

        # parser.add_argument('-s', '--scheduler', choices=schedulers, default=defaultScheduler,
        #                     help=clean_help('''The resource manager / scheduler your system uses.
        #                     Default is %s.''' % defaultScheduler))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from IPython.paths import get_ipython_dir
        import re
        import subprocess as subp

        # minutes = args.minutes
        # walltime = '%d:%02d:00' % (minutes/60, minutes%60)

        formatDict = {'scheduler': 'Slurm',       # support only SLURM for now
                      'account'  : args.account,
                      'engines'  : args.engines,
                      # 'walltime' : walltime
                      }

        profile = args.profile

        ipythonDir = get_ipython_dir()
        profileDir = os.path.join(ipythonDir, 'profile_' + profile)

        if os.path.isdir(profileDir):
            raise CommandlineError(f'Ipython profile directory "{profileDir}" already exists. Delete it or choose another name.')

        cmd = 'ipython profile create --parallel ' + profile
        _logger.info('Running command: %s', cmd)
        subp.call(cmd, shell=True)

        for basename, tuples in FileChanges.items():
            pathname = os.path.join(profileDir, basename)
            backup   = pathname + '~'

            if not os.path.isfile(pathname):
                raise CommandlineError(f'Missing configuration file: "{pathname}"')

            _logger.info(f'Editing config file: "{pathname}"')
            os.rename(pathname, backup)

            with open(backup, 'r') as input:
                lines = input.readlines()

            with open(pathname, 'w') as output:
                for line in lines:
                    for pattern, replacement in tuples:
                        if (m := re.match(pattern, line)):
                            line = replacement.format(**formatDict) + '\n'
                            break

                    output.write(line)
