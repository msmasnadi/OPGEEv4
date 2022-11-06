# Simple interface to some SLURM commands
#
# Copyright (c) 2022 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
import os
import re
import socket
import subprocess

from ..config import getParam
from ..log import getLogger
from ..subcommand import SubcommandABC

_logger = getLogger(__name__)

DEFAULT_RAY_PORT = 6379

TaskPattern = re.compile('^(\d+)\(x(\d+)\)')

def _tasks_by_node(tasks_per_node=None, job_nodelist=None, node_names=None):
    """
    Parse the packed formats of node names and tasks per node offered by SLURM
    to produce a list of (node_name, task_count) pairs. The keyword arguments are
    primarily for testing. In practice, this function will extract the values
    from environment variables.

    :param tasks_per_node: (str) must be in the same format as env variable
        $SLURM_TASKS_PER_NODE, e.g., '1(x2),7(x2),1,2,1'. If not provided,
        the environment variable will be used directly.
    :param job_nodelist: (str) must be in the same format as env variable
        $SLURM_JOB_NODELIST, e.g., 'sh02-01n[49-52,54-56]' If not provided,
        the environment variable will be used directly.
    :param node_names: (list of str) names of nodes. If provided, this list
        will be used instead of parsing ``job_nodelist`` or $SLURM_JOB_NODELIST.
    :return: (list) pairs of format (node_name, task count).
    """
    def get_counts(expr):
        if (m := re.match(TaskPattern, expr)):
            tasks = int(m.group(1))
            count = int(m.group(2))
            result = [tasks] * count
        else:
            result = [int(expr)]

        return result

    tasks = tasks_per_node or os.getenv('SLURM_TASKS_PER_NODE')
    counts = []
    for item in tasks.split(','):
        counts.extend(get_counts(item))

    if node_names is None:
        node_list = job_nodelist or os.getenv('SLURM_JOB_NODELIST')

        # pass nodelist to scontrol to expand into node names
        args = ['scontrol', 'show', 'hostnames', node_list]
        output = subprocess.run(args, check=True, text=True, capture_output=True)
        node_names = re.split('\s+', output.stdout.strip())

    pairs = zip(node_names, counts)
    return pairs

def start_ray_cluster(port):
    """
    Must be called from a script submitted with "sbatch" on SLURM. The sbatch command
    is told how many tasks to start; this function gets this info from the environment.

    Sbatch documentation says "When the job allocation is finally granted for the batch
    script, Slurm runs a single copy of the batch script on the first node in the set
    of allocated nodes."

    :return: the address (ip:port) of the head of the running ray cluster
    """
    import uuid
    from ..mcs.slurm import srun

    pairs = _tasks_by_node()
    node_dict = {node: count for node, count in pairs}

    host_name = socket.gethostname()
    ip_addr = socket.gethostbyname(host_name)
    address = f"{ip_addr}:{port}"

    # extract, e.g., 'sh03-ln02' from 'sh03-ln02.stanford.edu'
    head = host_name.split('.')[0]

    # Generate a UUID to use as redis password
    passwd = uuid.uuid4()

    _logger.info(f"Starting ray head on node {head} at {address}")
    srun(f'ray start --head --node-ip-address={ip_addr} --port={port} --redis-password={passwd} --block', head, sleep=30)

    # TBD: It's not this simple. The "head" involves several processes. Maybe head needs to
    #  allocate a whole node and assume cpu_count - N of the CPUs are available for workers?
    #  Need to know exactly how many processes Ray starts up. Looks like:
    #  1. ray start --head
    #  2. gcs_server
    #  3. monitor.py
    #  4. python ray.util.client.server
    #  5. python dashboard.py
    #  6. raylet
    #  7. python log_monitor.py
    #  8. python agent.py

    # Remove the head task from node_dict to leave only available worker tasks
    head_ntasks = node_dict[head]
    if head_ntasks == 1:
        del node_dict[head] # nothing else is available on this node
    else:
        node_dict[head] -= 1

    # Start the worker "raylets"
    for node, ntasks in node_dict.items():
        _logger.info(f"Starting {ntasks} worker on {node}")
        command = f'ray start --address={address} --num-cpus={ntasks} --redis-password={passwd} --block'
        srun(command, node, sleep=5)

    return address

class RayCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Start or stop a Ray cluster on SLURM.'''}
        super().__init__('ray', subparsers, kwargs)

    def addArgs(self, parser):
        addr_file = getParam('SLURM.RayAddressFile')

        parser.add_argument('mode', choices=['start', 'stop'],
                            help='''Whether to start or stop the Ray cluster. To start a Ray cluster, 
                                this command must be executed from a SLURM environment, e.g., using 
                                "sbatch [OPTIONS...] opg ray start". To stop a cluster, the file address 
                                containing the address of the Ray cluster must be visible.''')

        parser.add_argument('-A', '--address-file', default=None,
                            help=f'''The path to a file holding the address (ip:port) of the Ray
                                cluster "head". Default is the value of config var "SLURM.RayAddressFile",
                                currently "{addr_file}". The command 'opg ray start' writes this file, and
                                the commands "opg runsim" and "opg ray stop" both read it.''')

        parser.add_argument('-P', '--port', type=int, default=DEFAULT_RAY_PORT,
                            help=f"The port number to use for the Ray head. Default is {DEFAULT_RAY_PORT}")

        return parser

    def run(self, args, tool):
        import ray
        from ..error import OpgeeException

        addr_file = args.address_file or getParam('SLURM.RayAddressFile')

        if args.mode == 'start':
            if "SLURM_JOB_ID" not in os.environ:
                raise OpgeeException(f"'opg ray start' must be run in SLURM environment (i.e., using 'sbatch'.)")

            address = start_ray_cluster(args.port)

            # write the file to a temporary name and move it after closed to handle race condition
            _logger.debug(f'Writing address "{address}" to "{addr_file}')
            tmp_file = addr_file + '.tmp'
            with open(tmp_file, 'w') as f:
                f.write(address)

            os.rename(tmp_file, addr_file)

        else: # stop the Ray cluster
            with open(addr_file, 'r') as f:
                address = f.read().strip()

            ray.init(address=address)
            ray.shutdown()
            os.rename(addr_file, addr_file + '.stopped')


PluginClass = RayCommand
