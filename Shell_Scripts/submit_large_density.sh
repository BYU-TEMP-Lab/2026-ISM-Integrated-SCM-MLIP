#!/bin/bash
#SBATCH --job-name=Find_Density
#SBATCH --output=slurm_Density_%j.out
#SBATCH --time=03:00:00        # 1 hour is plenty of time
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4      # Give PyTorch some breathing room
#SBATCH --gpus=h200:1          # Request the GPU!
#SBATCH --mem=8G

module load miniforge3
mamba activate super_salt_env
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

# Define your massive 11-cation mixture and temperature
COMP=1.0MgCl2
TEMP=987

# Execute the Density Finder
python find_density.py --comp $COMP --temp $TEMP