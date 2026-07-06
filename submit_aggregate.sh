#!/bin/bash
#SBATCH --job-name=Aggregate_k
#SBATCH --output=slurm_aggregate_%j.out
#SBATCH --time=00:10:00        # 10 minutes is more than enough time
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1      # CPU only, no GPUs required
#SBATCH --mem=4G

# Load your environment
module load miniforge3
mamba activate super_salt_env

# Capture the variables passed from the master pipeline
COMP=$1
TEMP=$2

echo "Starting aggregation for $COMP at $TEMP K..."

python run_aggregate_pipeline.py --comp $COMP --temp $TEMP

echo "Aggregation complete!"