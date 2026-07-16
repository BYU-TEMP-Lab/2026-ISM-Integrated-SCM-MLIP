#!/bin/bash
# submit_master_pipeline.sh
# Usage: ./submit_master_pipeline.sh 0.5NaCl-0.5KCl 1100

COMP=$1
TEMP=$2

echo "Submitting full thermal conductivity pipeline for $COMP at $TEMP K"

# Load your environment so the Python parser runs correctly on the submit node
module load miniforge3
mamba activate super_salt_env

# 1. Parse the composition and check the CSV
# The python script outputs exactly "RK" or "MD"
METHOD=$(python check_density_method.py "$COMP")

# 2. Queue the appropriate Density Calculation based on the parser output
if [ "$METHOD" == "RK" ]; then
    echo "Using RK Empirical method for density (CPU only)..."
    DENS_ID=$(sbatch --parsable submit_rk_density.sh $COMP $TEMP)
else
    echo "Using MD method for density (GPU required)..."
    DENS_ID=$(sbatch --parsable submit_md_density.sh $COMP $TEMP)
fi

echo "Density Job ($METHOD): $DENS_ID"

# 3. Parallel Properties (1 GPU each, dependent on Density)
SCL_ID=$(sbatch --parsable --dependency=afterok:$DENS_ID submit_scl.sh $COMP $TEMP)
CP_ID=$(sbatch --parsable --dependency=afterok:$DENS_ID submit_cp.sh $COMP $TEMP)
KT_ID=$(sbatch --parsable --dependency=afterok:$DENS_ID submit_kt.sh $COMP $TEMP)

echo "SCL Job: $SCL_ID | Cp Job: $CP_ID | Kt Job: $KT_ID"

# 4. Vs Array (3 GPUs handled dynamically, dependent on Density)
VS_ID=$(sbatch --parsable --dependency=afterok:$DENS_ID submit_vs.sh $COMP $TEMP)
echo "Vs Array Job: $VS_ID"

# 5. Final Aggregation (CPU only, dependent on ALL previous jobs)
sbatch --dependency=afterok:$SCL_ID:$CP_ID:$KT_ID:$VS_ID submit_aggregate.sh $COMP $TEMP

echo "All jobs queued successfully!"
