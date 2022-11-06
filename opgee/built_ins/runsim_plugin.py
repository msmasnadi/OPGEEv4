#
# "runsim" sub-command to run a Monte Carlo simulation
#
# Author: Richard Plevin
#
# Copyright (c) 2022 The Board of Trustees of the Leland Stanford Junior University.
# See LICENSE.txt for license details.
#
import os

import ray

from ..log import getLogger
from ..subcommand import SubcommandABC

_logger = getLogger(__name__)

MODE_CLUSTER = 'cluster'
MODE_LOCAL = 'local'
KNOWN_MODES = [MODE_CLUSTER, MODE_LOCAL]

class RunsimCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : 'Run a Monte Carlo simulation using the model file stored in the simulation folder.'}
        super(RunsimCommand, self).__init__('runsim', subparsers, kwargs)

    def addArgs(self, parser):
        from ..config import getParam
        from ..utils import ParseCommaList
        from ..built_ins.ray_plugin import DEFAULT_RAY_PORT

        job_name  = getParam('SLURM.JobName')
        load_env  = getParam('SLURM.LoadEnvironment')
        partition = getParam('SLURM.Partition')
        addr_file = getParam('SLURM.RayAddressFile')
        log_file  = getParam('OPGEE.LogFile')

        # parser.add_argument('-a', '--analysis',
        #                     help='''The name of the analysis to run''')
        #
        # parser.add_argument('--overwrite', action='store_true',
        #                     help='''OVERWRITE prior results, if any.''')

        parser.add_argument('-a', '--address', default=None,
                            help='''The (ip:port) address of the Ray head process. Default is to use
                                the value of environment variable "RAY_ADDRESS" if it is not empty.''')

        parser.add_argument('-A', '--address-file', default=None,
                            help=f'''The path to a file holding the address (ip:port) of the Ray
                                cluster "head". Default is the value of config var "SLURM.RayAddressFile",
                                currently {addr_file}''')

        parser.add_argument('-c', '--cpu-count', type=int, default=0,
                            help='''The number of CPUs to use to run the MCS. A value of zero
                                means use all available CPUs. Ignored if --mode=cluster is specified,
                                in which case all available CPUs on the remote cluster are used.''')

        parser.add_argument('-d', "--no-delete", action='store_true',
                            help="Don't delete the temporary file (useful primarily for debugging.)")

        # parser.add_argument('-D', '--debug', action='store_true',
        #                     help="Show but don't run SLURM commands. Implies --no-delete.")

        parser.add_argument('--debug', action='store_true',
                            help='''Use the Manager/Worker architecture, but don't use "ray" 
                            (primarily for debugging Worker code)''')

        parser.add_argument('-e', "--load-env", default="",
                            help=f'''A command to load your python and/or module environment. Default 
                                is the value of config variable "SLURM.LoadEnvironment, currently 
                                '{load_env}'".''')

        parser.add_argument('-f', '--fields', action=ParseCommaList,
                            help='''Run only the specified field or fields. Argument may be a 
                            comma-delimited list of Field names. Otherwise all fields defined in the
                            analysis are run.''')

        parser.add_argument('-j', "--job-name", default=None,
                            help=f'''The job name. Default is value of config variable "SLURM.JobName",
                            currently '{job_name}'.''')

        parser.add_argument('-l', "--log-file", default=None,
                            help=f'''The path to the logfile to create. Default is the value of config
                                variable 'OPGEE.LogFile', currently {log_file}'.''')

        parser.add_argument('-m', '--mode', choices=KNOWN_MODES, default=MODE_LOCAL,
                            help=f'''Whether to run on the local node or user's computer ("{MODE_LOCAL}"), or to 
                                connect to an existing cluster ("{MODE_CLUSTER}"). Default is "{MODE_LOCAL}". 
                                Mode is ignored if --debug is specified, since "ray" isn't used in that case.''')

        parser.add_argument('-n', "--ntasks", type=int, default=1,
                            help="Number of worker tasks to create. Default is the number of fields.")

        parser.add_argument('-p', "--partition", default=None,
                            help=f'''The name of the partition to use for job submissions. Default is the
                                 value of config variable "SLURM.Partition", currently '{partition}'.''')

        parser.add_argument('-P', '--port', type=int, default=DEFAULT_RAY_PORT,
                            help=f'''The port number to use the "head" of the Ray cluster. 
                                Default is {DEFAULT_RAY_PORT}''')

        parser.add_argument('-s', '--simulation-dir',
                            help='''The top-level directory to use for this simulation "package"''')

        parser.add_argument('-S', '--serial', action='store_true',
                            help="Run the simulation serially in the currently running process.")

        parser.add_argument('-t', '--trials', default='all',
                            help='''The trials to run. Can be expressed as a string containing
                            comma-delimited ranges and individual trail numbers, e.g. "1-20,22, 35, 42, 44-50").
                            The special string "all" (the default) runs all defined trials.''')

        # TBD: make this a config variable
        parser.add_argument('--time', default='60',
                            help=f'''The amount of wall time to allocate for each task. Default is 60 minutes.
                                Acceptable time formats include "minutes", "minutes:seconds", "hours:minutes:seconds",
                                and formats involving days, which we shouldn't require.''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        import os
        import time
        from ..config import getParam
        from ..utils import parseTrialString
        from ..mcs.simulation import Simulation
        from ..mcs.distributed_mcs import Manager
        from ..mcs.slurm import sbatch_het_job

        sim_dir = args.simulation_dir
        field_names = args.fields       # TBD: if not set, get fields from XML

        if args.serial:
            sim = Simulation(sim_dir, field_names=field_names)
            trial_nums = (None if args.trials == 'all' else parseTrialString(args.trials))
            sim.run(trial_nums)

        else:
            if args.mode == MODE_CLUSTER:
                job_name = args.job_name or getParam('SLURM.JobName')
                partition = args.partition or getParam('SLURM.Partition')
                addr_file = args.address_file

                try:
                    os.remove(addr_file)
                except FileNotFoundError:
                    pass  # ok if it doesn't exist

                # "opg ray start" writes the ray head address to the address-file
                command = f'opg ray start --port={args.port} --address-file="{addr_file}"'

                # Create a ray cluster with the given number of worker tasks
                sbatch_het_job(command,
                               # head node configuration
                               dict(ntasks=8,       # the number of processes run by "ray start --head"
                                    nodes="1:1",
                                    time=args.time,
                                    partition=partition,
                                    job_name=job_name,
                                    mem_per_cpu=getParam('SLURM.MemPerCPU')),

                               # worker node configuration
                               dict(ntasks=args.ntasks,
                                    mem_per_cpu=getParam('SLURM.MemPerCPU'),
                                    ),
                               sleep=5)

                # Wait for addr_file to appear
                while not os.path.exists(addr_file):
                    _logger.debug("Waiting for '{addr_file}' to be written.")
                    time.sleep(5)

                with open(addr_file, 'r') as f:
                    address = f.read().strip()

                # Wait until we connect to Ray cluster
                while True:
                    try:
                        ray.init(address=address)
                    except ConnectionError:
                        time.sleep(5)
                        continue

                    break

            mgr = Manager(address=address, mode=args.mode)
            mgr.run_mcs(sim_dir, field_names=field_names, cpu_count=args.cpu_count,
                        trial_nums=args.trials, debug=args.debug)

