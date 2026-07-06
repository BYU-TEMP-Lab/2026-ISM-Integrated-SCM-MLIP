#!/bin/bash
# submit_master_pipeline.sh
# Usage: ./submit_master_pipeline.sh 0.5NaCl-0.5KCl 1100

COMP=$1
TEMP=$2

echo "Submitting full thermal conductivity pipeline for $COMP at $TEMP K"

# 1. Density Calculation (Outputs density_output.txt)
DENS_ID=$(sbatch --parsable submit_density.sh $COMP $TEMP)
echo "Density Job: $DENS_ID"

# 2. Parallel Properties (1 GPU each, dependent on Density)
SCL_ID=$(sbatch --parsable --dependency=afterok:$DENS_ID submit_scl.sh $COMP $TEMP)
CP_ID=$(sbatch --parsable --dependency=afterok:$DENS_ID submit_cp.sh $COMP $TEMP)
KT_ID=$(sbatch --parsable --dependency=afterok:$DENS_ID submit_kt.sh $COMP $TEMP)

echo "SCL Job: $SCL_ID | Cp Job: $CP_ID | Kt Job: $KT_ID"

# 3. Vs Array (3 GPUs handled dynamically, dependent on Density)
VS_ID=$(sbatch --parsable --dependency=afterok:$DENS_ID submit_vs.sh $COMP $TEMP)
echo "Vs Array Job: $VS_ID"

# 4. Final Aggregation (CPU only, dependent on ALL previous jobs)
sbatch --dependency=afterok:$SCL_ID:$CP_ID:$KT_ID:$VS_ID submit_aggregate.sh $COMP $TEMP

echo "All jobs queued successfully!"