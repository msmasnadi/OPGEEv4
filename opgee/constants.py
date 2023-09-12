#
# String constants
#
CLUSTER_NONE  = 'serial'  # no cluster; just run fields serially
CLUSTER_LOCAL = 'local'
CLUSTER_SLURM = 'slurm'
CLUSTER_TYPES = (CLUSTER_NONE, CLUSTER_SLURM, CLUSTER_LOCAL)
