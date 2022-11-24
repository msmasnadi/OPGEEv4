#!/bin/bash
#SBATCH --nodes=4
#SBATCH --job-name=test
#SBATCH --time=00:05:00
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-task=0
#SBATCH --cpus-per-task=1

#
# Modified from https://github.com/ray-project/ray/issues/26477
#
# Original stuff
##SBATCH --image=registry.nersc.gov/das/delta:5.0
##SBATCH --qos=debug
##SBATCH -A dasrepo_g
##SBATCH -C gpu

set -x

#SHIFTER=shifter   # original code
SHIFTER=""         # non-shifter version

# Getting the node names
nodes=$(scontrol show hostnames "$SLURM_JOB_NODELIST")
nodes_array=($nodes)
head_node=${nodes_array[0]}
head_node_ip=$(srun --nodes=1 --ntasks=1 -w "$head_node" hostname --ip-address)
# if we detect a space character in the head node IP, we'll
# convert it to an ipv4 address. This step is optional.
if [[ "$head_node_ip" == *" "* ]]; then
IFS=' ' read -ra ADDR <<<"$head_node_ip"
if [[ ${#ADDR[0]} -gt 16 ]]; then
  head_node_ip=${ADDR[1]}
else
  head_node_ip=${ADDR[0]}
fi
echo "IPV6 address detected. We split the IPV4 address as $head_node_ip"
fi

port=6379
ip_head=$head_node_ip:$port
export ip_head
echo "IP Head: $ip_head"
echo "Starting HEAD at $head_node"

srun -u --nodes=1 --ntasks=1 -w "$head_node" \
  $SHIFTER ray start --head --node-ip-address="$head_node_ip" --port=$port \
    --num-cpus "${SLURM_CPUS_PER_TASK}" --num-gpus "${SLURM_GPUS_PER_TASK}" --block &

# number of nodes other than the head node
worker_num=$((SLURM_JOB_NUM_NODES - 1))

for ((i = 1; i <= worker_num; i++)); do
    node_i=${nodes_array[$i]}
    echo "Starting WORKER $i at $node_i"
    srun -u --nodes=1 --ntasks=1 -w "$node_i" \
     $SHIFTER ray start --address "$ip_head" \
        --num-cpus "${SLURM_CPUS_PER_TASK}" --num-gpus "${SLURM_GPUS_PER_TASK}" --block &
    sleep 5
done

#${SHIFTER} python3 -u test.py

addr_file=$(opg config -x Ray.AddressFile)
opg ray start --port=$port --address-file="$addr_file"
