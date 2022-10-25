#
# Adapted from launch.py from https://github.com/pengzhenghao/use-ray-with-slurm.git
#
from opgee.subcommand import SubcommandABC

class LaunchCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Launch a Ray cluster on SLURM'''}
        super().__init__('launch', subparsers, kwargs)

    def addArgs(self, parser):
        '''
        Process the command-line arguments for this sub-command
        '''
        DEFAULT_RAY_PORT = 6379

        parser.add_argument("command",
                            help='''The command you wish to execute. For example: 
                                'opg launch "opg runsim -d -s simulation-dir -t 0-99"' 
                                Note that the command usually needs to be quoted.''')

        parser.add_argument('-d', "--no-delete", action='store_true',
                            help="Don't delete the temporary file (useful primarily for debugging.)")

        parser.add_argument('-D', '--debug', action='store_true',
                            help="Show but don't run SLURM commands. Implies --no-delete.")

        parser.add_argument('-e', "--load-env", default="",
                            help='''A command to load your environment. Default is the value of 
                                config variable "SLURM.LoadEnvironment".''')

        parser.add_argument('-j', "--job-name", default=None,
                            help=f'''The job name. Default is value of config variable "SLURM.JobName".''')

        parser.add_argument('-l', "--log-file", default=None,
                            help=f'''The path to the logfile to create. Default is the value of config
                                variable 'OPGEE.LogFile'.''')

        parser.add_argument('-N', "--node", default="",
                            help='''The specified nodes to use. Same format as the return of 'sinfo'. 
                            Default is ''.''')

        parser.add_argument('-n', "--num-nodes", type=int, default=1,
                            help="Number of nodes to use. Default is 1.")

        parser.add_argument('-g', "--num-gpus", type=int, default=0,
                            help="Number of GPUs to use in each node. Default is 0.")

        parser.add_argument('-p', "--partition", default=None,
                            help='''The name of the partition to use for job submissions. Default is the
                                value of config variable "SLURM.Partition".''')

        parser.add_argument('-P', '--port', type=int, default=DEFAULT_RAY_PORT,
                            help=f"The port number to use for the Ray head. Default is {DEFAULT_RAY_PORT}")

        return parser

    def run(self, args, tool):
        import subprocess
        import tempfile
        from ..config import getParam, getParamAsBoolean
        from ..utils import getResource

        JOB_NAME = "{{JOB_NAME}}"
        LOG_FILE = "{{LOG_FILE}}"
        NUM_NODES = "{{NUM_NODES}}"
        NUM_GPUS_PER_NODE = "{{NUM_GPUS_PER_NODE}}"
        PARTITION_NAME = "{{PARTITION_NAME}}"
        COMMAND = "{{COMMAND}}"
        COMMAND_SUFFIX = "{{COMMAND_SUFFIX}}"
        GIVEN_NODE = "{{GIVEN_NODE}}"
        LOAD_ENV = "{{LOAD_ENV}}"
        PORT_NUMBER = "{{PORT_NUMBER}}"

        # Automatically select debug mode if SLURM isn't available
        debug = args.debug or not getParamAsBoolean('SLURM.Available')

        log_file = args.log_file or getParam('SLURM.LogFile')
        job_name = args.job_name or getParam('SLURM.JobName')
        partition = args.partition or getParam('SLURM.Partition')
        load_env = args.load_env or getParam('SLURM.LoadEnvironment')

        node_info = f"#SBATCH -w {args.node}" if args.node else ""
        # read the template script from the opgee package
        text = getResource('mcs/etc/sbatch_template.sh')

        # modify the template script per command-line args
        text = text.replace(PARTITION_NAME, partition)
        text = text.replace(JOB_NAME, job_name)
        text = text.replace(LOG_FILE, log_file)
        text = text.replace(NUM_NODES, str(args.num_nodes))
        text = text.replace(NUM_GPUS_PER_NODE, str(args.num_gpus))
        text = text.replace(GIVEN_NODE, node_info)
        text = text.replace(PORT_NUMBER, str(args.port))
        text = text.replace(COMMAND, args.command)
        text = text.replace(COMMAND_SUFFIX, "")
        text = text.replace(LOAD_ENV, load_env)
        text = text.replace(
            "# THIS FILE IS A TEMPLATE AND IT SHOULD NOT BE DEPLOYED TO PRODUCTION!",
            "# THIS FILE IS MODIFIED AUTOMATICALLY FROM A TEMPLATE AND SHOULD BE RUNNABLE."
        )

        delete = not (args.no_delete or debug)

        with tempfile.NamedTemporaryFile(mode='w', suffix=".sh", delete=delete) as fp:
            script_file = fp.name
            fp.write(text)
            fp.flush()  # file is deleted when closed, so flush all output but leave it open

            if args.debug:
                print(f"sbatch '{script_file}'")
            else:
                # Submit the job
                print("Start to submit job!")
                subprocess.Popen(["sbatch", script_file])

                script_msg = "" if delete else "Script file: '{script_file}'."
                print(f"Job submitted. Log file: '{args.log_file}'.{script_msg}")


# An alternative to naming the class 'Plugin' is to assign the class to PluginClass
PluginClass = LaunchCommand

