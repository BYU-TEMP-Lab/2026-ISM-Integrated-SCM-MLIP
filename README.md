# 2026-ISM--Integrated-SCM-MLIP
This repository contains the code and slurm files required to run the ISM through a HPC Cluster.

Download all python files in the "Pipeline" folder, all shell scripts in the "Shell_Scripts" folder, and the "SuperSalt-swa.model" file from the data availablity section of the original SuperSalt paper: "https://doi.org/10.5281/zenodo.15734798".

Thermal conductivity can be predicted by entering a command in the following format: "./submit_master_pipeline.sh 0.32MgCl2-0.68KCl 800" for the case of 0.32MgCl2-0.68KCl at 800 K. 

Currently, if the salt mixture has components for which the Redlich-Kister excess terms are not calculated, this command will throw an error and the user needs to run a short MD simulation predicting density using the SuperSalt potential. The files needed for this are in the folder "Manual_Density". 

Development is currently being done to automate this part of the workflow as well, so that if the RK model cannot be used, the MD simulation for density will be queued automatically.

In the case of any failed simulations, the shell scripts and python files needed to run single simulations are in the folder "Reruns". Once all four properties, cp, vs, scl, and kt, have a txt file associated with their value, thermal conductivity can be calculated using the "submit_missed_aggregate.sh" shell script. 
