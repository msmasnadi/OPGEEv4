#!/bin/sh
#SBATCH --time=10:00
#SBATCH --array=0-49
#SBATCH --mem-per-cpu=500MB

# Or perhaps just #SBATCH --ntasks=50 ?

# When using --array, each task sees only one node (its own)
nodes=$(scontrol show hostnames $SLURM_JOB_NODELIST)

echo "Nodes: $nodes"

echo "SLURM_ARRAY_JOB_ID: $SLURM_ARRAY_JOB_ID"
echo "SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID"
echo "SLURM_ARRAY_TASK_MIN: $SLURM_ARRAY_TASK_MIN"

port={{PORT_NUMBER}}
IP_HEAD=$ip:$port
export IP_HEAD

echo "IP Head: $IP_HEAD"

export RAY_ADDRESS="ray://$IP_HEAD"

echo "Ray address: $RAY_ADDRESS"


if [ $SLURM_ARRAY_TASK_MIN == $SLURM_ARRAY_TASK_ID ]; then
    echo "I am the manager task"
    # 
    # redis_password=$(uuidgen)
    # export redis_password

    # nodes=$(scontrol show hostnames $SLURM_JOB_NODELIST) # get the node names
    # nodes_array=($nodes)

    # node_1=${nodes_array[0]}
    # ip=$(srun --nodes=1 --ntasks=1 -w $node_1 hostname --ip-address) # make redis-address

else
    echo "I am a worker task"
fi
