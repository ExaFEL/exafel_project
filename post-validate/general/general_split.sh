#!/bin/bash
SRUN="srun -c 2"

H5_SIM_PATH=$1
H5_SIM_PATH=${H5_SIM_PATH%/} # remove any trailing forward slash
export SPEC_PATH=${H5_SIM_PATH}/integ_exp_ref.txt

echo "jobstart $(date)";pwd
$SRUN diffBragg.make_input_file ${H5_SIM_PATH}/index $SPEC_PATH
echo "jobend $(date)";pwd
