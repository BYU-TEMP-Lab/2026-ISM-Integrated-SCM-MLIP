# Integrated structural coherence model (SCM) and machine-learning interatomic potential (MLIP)

This repository contains the code and slurm files required to run the ISM through a HPC Cluster.

This pipeline is from the paper:
> **Integration of a Structural Coherence Model with a Semi-Universal Machine Learning Interatomic Potential to Predict Molten Salt Thermal Conductivity** (Walker et al., 2026). DOI: 10.21203/rs.3.rs-10223172/v1

## Set-up Instructions

### Download necessary files

Create a virtual environment, using the "super_salt_env" yml file.

Download all python files in the "Pipeline" folder, all shell scripts in the "Shell_Scripts" folder, and the "SuperSalt-swa.model" file from the data availablity section of the original SuperSalt paper: "https://doi.org/10.5281/zenodo.15734798". For the density prediction using the ORNL Redlich-Kister model, request access to the MSD-TP through the link: https://msd.ornl.gov/access-instructions/
Download the csv files "Molten_Salt_Thermophysical_Properties_rho_RK" and "Molten_Salt_Thermophysical_Properties" in order to run the RK_density.py file as written. 

If unable to access the MSD-TP, the pipeline will automatically run a short (~10-20 min) simulation using SuperSalt to approximate the density.

Once all of these files are in the same folder, the pipeline is ready to be used. The current shell scripts are set for H200 GPUs, but this can be changed to whatever GPU the user would like to use. The time should be adjusted as necessary if operating on a HPC cluster that requires estimated time inputs. Current times are set for H200 NVDIA GPUs.


### Enter desired composition and temperature into command line
Thermal conductivity can be predicted by entering a command in the following format: "./submit_master_pipeline.sh 0.32MgCl2-0.68KCl 800" for the case of 0.32MgCl2-0.68KCl at 800 K. 

### Debugging
Sometimes a MD simulation may fail, and the aggregate script will never run. In that case, rerun the failed MD simulation, and then run the aggregate script again.

The shell scripts and python files needed to run single simulations are in the folder "Reruns". Once all four properties, cp, vs, scl, and kt, have a txt file associated with their value, thermal conductivity can be calculated using the "submit_missed_aggregate.sh" shell script. 
