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

        job_name  = getParam('SLURM.JobName')
        load_env  = getParam('SLURM.LoadEnvironment')
        partition = getParam('SLURM.Partition')
        min_per_task = getParam('SLURM.MinutesPerTask')
        addr_file = getParam('Ray.AddressFile')
        dflt_port = getParam('Ray.Port')
        dflt_mode = getParam('OPGEE.RunsimMode')
        log_file  = getParam('OPGEE.LogFile')

        # parser.add_argument('-a', '--analysis',
        #                     help='''The name of the analysis to run''')
        #
        # parser.add_argument('--overwrite', action='store_true',
        #                     help='''OVERWRITE prior results, if any.''')

        parser.add_argument('-a', '--address', default=None,
                            help='''The (ip:port) address of the Ray head process. Default is to use
                                the value of environment variable "RAY_ADDRESS" if it is not empty.''')

        parser.add_argument('-A', '--address-file', default=addr_file,
                            help=f'''The path to a file holding the address (ip:port) of the Ray
                                cluster "head". Default is the value of config var "Ray.AddressFile",
                                currently {addr_file}''')

        parser.add_argument('-c', '--cpu-count', type=int, default=0,
                            help='''The number of CPUs to use to run the MCS. A value of zero
                                means use all available CPUs. Ignored if --mode=cluster is specified,
                                in which case all available CPUs on the remote cluster are used.''')

        parser.add_argument('-d', "--no-delete", action='store_true',
                            help="Don't delete the temporary file (useful primarily for debugging.)")

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

        parser.add_argument('-m', '--mode', choices=KNOWN_MODES, default=dflt_mode,
                            help=f'''Whether to run on the local node or user's computer ("{MODE_LOCAL}"), or to 
                                connect to an existing cluster ("{MODE_CLUSTER}"). Default is "{dflt_mode}". 
                                Mode is ignored if --debug is specified, since "ray" isn't used in that case.''')

        parser.add_argument('-n', "--ntasks", type=int, default=None,
                            help='''Number of worker tasks to create. Default is the number of fields, if
                                specified using -f/--fields, otherwise -n/--ntasks is required.''')

        parser.add_argument('-p', "--partition", default=None,
                            help=f'''The name of the partition to use for job submissions. Default is the
                                 value of config variable "SLURM.Partition", currently '{partition}'.''')

        parser.add_argument('-P', '--port', type=int, default=dflt_port,
                            help=f'''The port number to use the "head" of the Ray cluster. Default is
                             the value of config var "Ray.Port", currently {dflt_port}''')

        parser.add_argument('-s', '--simulation-dir',
                            help='''The top-level directory to use for this simulation "package"''')

        parser.add_argument('-S', '--serial', action='store_true',
                            help="Run the simulation serially in the currently running process.")

        parser.add_argument('-t', '--trials', default='all',
                            help='''The trials to run. Can be expressed as a string containing
                            comma-delimited ranges and individual trail numbers, e.g. "1-20,22, 35, 42, 44-50").
                            The special string "all" (the default) runs all defined trials.''')

        parser.add_argument('--time', default=min_per_task,
                            help=f'''The amount of wall time to allocate for each task. Default is 
                                {min_per_task} minutes. Acceptable time formats include "minutes", 
                                "minutes:seconds", "hours:minutes:seconds", and formats involving days, 
                                which we shouldn't require.''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        import os
        import time
        from ..config import getParam, getParamAsInt
        from ..error import OpgeeException
        from ..utils import parseTrialString
        from ..mcs.simulation import Simulation
        from ..mcs.distributed_mcs import Manager
        from ..mcs.slurm import sbatch, sbatch_het_job

        sim_dir = args.simulation_dir
        field_names = args.fields       # TBD: if not set, get fields from XML

        ntasks = args.ntasks

        if ntasks is None:
            if field_names:
                ntasks = len(field_names)
            else:
                raise OpgeeException(f"Must specify field names (-f/--fields) or -n/--ntasks")

        if args.serial:
            sim = Simulation(sim_dir, field_names=field_names)
            trial_nums = (None if args.trials == 'all' else parseTrialString(args.trials))
            sim.run(trial_nums)

        else:
            if args.mode == MODE_CLUSTER:
                job_name = args.job_name or getParam('SLURM.JobName')
                partition = args.partition or getParam('SLURM.Partition')
                head_procs = getParamAsInt("Ray.HeadProcs")
                addr_file = args.address_file

                try:
                    os.remove(addr_file)
                except FileNotFoundError:
                    pass  # ok if it doesn't exist

                # "opg ray start" writes the ray head address to the address-file
                command = f'opg ray start --port={args.port} --address-file="{addr_file}"'

                homogenous = True

                if homogenous:
                    # compute number of nodes required for ntasks
                    cores = getParamAsInt('SLURM.MinimumCoresPerNode')
                    worker_nodes = ntasks // cores + (1 if ntasks % cores else 0)

                    sbatch(command, sleep=15,
                           partition=partition,
                           job_name=job_name,
                           nodes=worker_nodes + 1,
                           ntasks_per_node=1,
                           time=args.time,
                           )
                else:
                    # Submit a heterogeneous job to SLURM. (Never got this to work...)
                    # Create a ray cluster with the given number of worker tasks
                    sbatch_het_job(command,
                                   # Ray head configuration
                                   dict(chdir=getParam('SLURM.RunDir'),
                                        partition=partition,
                                        job_name=job_name,
                                        nodes=1,
                                        tasks_per_node=1,
                                        ntasks=1,
                                        cpus_per_task=head_procs,
                                        time=args.time,
                                        ),

                                   # Ray worker configuration
                                   dict(ntasks=1,
                                        cpus_per_task=1,
                                        time=args.time,
                                        ),

                                   sleep=15)

                # Wait for addr_file to appear
                while not os.path.exists(addr_file):
                    _logger.debug(f"Waiting for '{addr_file}' to be written.")
                    time.sleep(10)

                with open(addr_file, 'r') as f:
                    address = f.read().strip()

                # Wait until we connect to Ray cluster
                while True:
                    _logger.debug(f"Waiting for Ray to become available")
                    try:
                        ray.init(address=address)
                    except ConnectionError:
                        time.sleep(5)
                        continue

                    break

            mgr = Manager(address=address, mode=args.mode)
            mgr.run_mcs(sim_dir, field_names=field_names, cpu_count=args.cpu_count,
                        trial_nums=args.trials, debug=args.debug)
