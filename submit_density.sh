#!/bin/bash
#SBATCH --job-name=Calc_Density
#SBATCH --output=slurm_density_%j.out
#SBATCH --time=00:10:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G

# Load your environment
module load miniforge3
mamba activate super_salt_env

COMP=$1
TEMP=$2

# Call the Python script (assuming FLiNaK fractions for example, adjust logic as needed)
# In production, you might want to pass x1 and x2 from the master script too!
python RK_Density.py --comp $COMP --temp $TEMP --out density_${COMP}_${TEMP}K.txt