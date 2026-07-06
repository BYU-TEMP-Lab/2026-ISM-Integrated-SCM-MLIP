#!/bin/bash
#SBATCH --job-name=Vs_Array
#SBATCH --output=slurm_vs_%A_%a.out  
#SBATCH --time=14:00:00               
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1            
#SBATCH --gpus=h200:1
#SBATCH --mem=6G                
#SBATCH --array=41-43               

module load miniforge3
mamba activate super_salt_env
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

COMP=$1
TEMP=$2
DENSITY=$(cat density_${COMP}_${TEMP}K.txt)

# Execute Python with the unique array ID as the seed
python run_vs_pipeline.py --comp $COMP --temp $TEMP --density $DENSITY --seed $SLURM_ARRAY_TASK_ID