#!/bin/bash
#SBATCH --job-name=Calc_Kt
#SBATCH --output=slurm_Kt_%j.out
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --gpus=h200:1  # Request 1 GPU
#SBATCH --mem=6G

module load miniforge3
mamba activate super_salt_env
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

COMP=$1
TEMP=$2

DENSITY=$(cat density_${COMP}_${TEMP}K.txt)

python run_kt_pipeline.py --comp $COMP --temp $TEMP --density $DENSITY