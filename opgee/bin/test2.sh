#!/bin/bash
#SBATCH --time=3:00
#SBATCH --mem-per-cpu=500MB
#SBATCH --ntasks=20

echo "SLURM_JOB_NODELIST: $SLURM_JOB_NODELIST"
echo "SLURM_JOB_CPUS_PER_NODE: $SLURM_JOB_CPUS_PER_NODE"
echo "SLURM_TASKS_PER_NODE: $SLURM_TASKS_PER_NODE"

# Expand the abbreviated hostnames (e.g., "sh02-01n[25,32,37,49,51-52,54]"
nodes=($(scontrol show hostnames $SLURM_JOB_NODELIST))
echo "Nodes: ${nodes[*]}"

exit

# Load modules and conda environment
module load viz
conda act opgee


# Use the first node in the list as the "head" for ray and the rest as workers
head=${nodes[0]}
workers=${nodes[*]:1}

ip=$(srun --nodes=1 --ntasks=1 -w $head hostname --ip-address)
port=6379
IP_HEAD=$ip:$port
export IP_HEAD
echo "IP Head: $IP_HEAD"

export RAY_ADDRESS="ray://$IP_HEAD"
echo "Ray address: $RAY_ADDRESS"

redis_password=$(uuidgen)
export redis_password

#
# Start "head" task
#
echo "STARTING HEAD at $head"
srun --nodes=1 --ntasks=1 --nodelist $head \
  ray start --head --address=$IP_HEAD --redis-password=$redis_password --block &
  # used 2 args instead of --address originally:
  # ray start --head --node-ip-address=$ip --port=$port --redis-password=$redis_password --block &

sleep 30   # give the head time to start up so workers can find it



# Alternatively, call sbatch --array, but with the above parameters set in the environment like:
#   sbatch --array=100 ray start --address=$IP_HEAD --redis-password=$redis_password --block &
#
# - or -
#
#  salloc to get all the resources up front, then run a single command that does all of this
#  $SLURM_JOB_NODELIST has the list of nodes and
#  $SLURM_JOB_CPUS_PER_NODE has the count of CPUs allocated on each node in $SLURM_JOB_NODELIST
#  format is '72(x2),36' with (x2) meaning the first 2 nodes have 72 CPUs allocated.
#  Could use $SLURM_TASKS_PER_NODE instead since we're using one CPU per task.
#  Note: these env vars are available with sbatch as well
#
# Running sbatch with --ntasks=10 resulted in one logfile with these contents:
# tasks where actually allocated
#  SLURM_JOB_NODELIST: sh02-01n[25,32,37,49,51-52,54]
#  SLURM_JOB_CPUS_PER_NODE: 3,1(x3),2,1(x2)
#  SLURM_TASKS_PER_NODE: 3,1(x3),2,1(x2)
#
# With --ntasks=20, got this:
#  SLURM_JOB_NODELIST: sh02-01n[49-52,54-56]
#  SLURM_JOB_CPUS_PER_NODE: 1(x2),7(x2),1,2,1
#  SLURM_TASKS_PER_NODE: 1(x2),7(x2),1,2,1

#
# Start worker tasks
#
for node in $workers; do
  echo "Starting worker $i at $node"
  # TBD: is --nodes=1 necessary?
  srun --nodes=1 --ntasks=1 --nodelist $node \
      ray start --address=$IP_HEAD --redis-password=$redis_password --block &

  sleep 5
done

# opg runsim --address=$IP_HEAD 
