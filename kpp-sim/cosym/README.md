<h2>This directory presents various cases exercising the cosym feature of the merging program on Perlmutter. 08/01/2023.</h2>

Github branch pre-requisites:<br>
cctbx_project/nxmx_writer_experimental<br>
dials/dsp_nv_outlier_disable

```
Cases:
PDB code 7m75: Photosystem I, space group P63 (one twin law)
PDB code 5sya: DJ1, space group P321 (one twin law)
PDB code 4qfl: AF binding protein (three twin laws)
```

Batch jobs are submitted from the user's choice directory ${WORK}.  However, it is assumed there is a directory, ${SCRATCH}/cosym, available for fast I/O.
The JOB_ID for each step is saved in an environment variable so it can be used to locate files for subsequent steps.

Simulation step:

```
export JOB_ID_SIM=`sbatch $MODULES/exafel_project/kpp-sim/cosym/4qfl_P32_cosym_sim.sh|awk '{print $4}'`
echo SIM $JOB_ID_SIM
```

Cctbx: dials.stills_process:
```
export JOB_ID_INDEX=`sbatch $MODULES/exafel_project/kpp-sim/cosym/4qfl_P32_cosym_index.sh $JOB_ID_SIM|awk '{print $4}'`
echo INDEX $JOB_ID_INDEX
```

Cctbx.xfel.merge:
```
export JOB_ID_MERGE=`sbatch $MODULES/exafel_project/kpp-sim/cosym/4qfl_P32_cosym_merge.sh $JOB_ID_SIM $JOB_ID_INDEX|awk '{print $4}'`
echo MERGE $JOB_ID_MERGE
```


