<h2>This directory presents the processing case of 130,000 diffraction patterns from Yb-Lysozyme, on Perlmutter. 08/01/2023.</h2>

Github branch pre-requisites:<br>
cctbx_project/nxmx_writer_experimental<br>
dxtbx/nxmx_writer<br>
dials/dsp_nv_outlier_disable

Batch jobs are submitted from the user's choice directory ${WORK}.  However, it is assumed there is a directory, ${SCRATCH}/yb_lyso, available for fast I/O.
The JOB_ID for each step is saved in an environment variable so it can be used to locate files for subsequent steps.

Simulation step:

```
export JOB_ID_SIM=`sbatch $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_sim.sh|awk '{print $4}'`
echo SIM $JOB_ID_SIM
```

Cctbx: dials.stills_process:
```
export JOB_ID_INDEX=`sbatch $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_index.sh $JOB_ID_SIM|awk '{print $4}'`
echo INDEX $JOB_ID_INDEX
```

Cctbx.xfel.merge:
```
export JOB_ID_MERGE=`sbatch $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_merge.sh $JOB_ID_INDEX|awk '{print $4}'`
echo MERGE $JOB_ID_MERGE
```

Make input step, splits files:

```
export JOB_ID_SPLIT=`sbatch $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_split.sh $JOB_ID_INDEX|awk '{print $4}'`
echo SPLIT $JOB_ID_SPLIT
```

Stage 1, hopper:

```
export JOB_ID_HOPPER=`sbatch $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_stage1.sh $SCRATCH/yb_lyso/${JOB_ID_MERGE}/out/ly99sim_all.mtz $SCRATCH/yb_lyso/${JOB_ID_SPLIT}_integ_exp_ref.txt|awk '{print $4}'`
echo HOPPER ${JOB_ID_HOPPER}
```

Integrate and predict step:
```
export JOB_ID_INTEGRATE=`sbatch $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_predict.sh ${JOB_ID_HOPPER} | awk '{print $4}'`
echo INTEGRATE ${JOB_ID_INTEGRATE}
```

Double check that the Pandas pickle table has one row for each image (about 130,000):
```
libtbx.python
import pandas
df = pandas.read_pickle("${JOB_ID_INTEGRATE}/predict/preds_for_hopper.pkl")
len(df)
```
DiffBragg stage 2:
```
export JOB_ID_STAGE2=`sbatch $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_stage2.sh ${JOB_ID_INDEX} ${JOB_ID_MERGE} ${JOB_ID_INTEGRATE} | awk '{print $4}'`
echo STAGE2 ${JOB_ID_STAGE2}
```
Elementary check on structure factor convergence over 450 iterations:
```
libtbx.ipython $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/yb_lyso/${JOB_ID_MERGE}/out/ly99sim_all.mtz stage2=$SCRATCH/yb_lyso/${JOB_ID_STAGE2}/${JOB_ID_STAGE2} pdb=${MODULES}/cxid9114/sim/4bs7.pdb n_bins=8 d_min=2.3
```
If you are confident all the steps will run without failure you can submit them in a single
block with SLURM dependencies:
```
export JOB_ID_SIM=`sbatch $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_sim.sh|awk '{print $4}'`
echo SIM $JOB_ID_SIM

export JOB_ID_INDEX=`sbatch --dependency=afterok:${JOB_ID_SIM} $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_index.sh $JOB_ID_SIM|awk '{print $4}'`
echo INDEX $JOB_ID_INDEX

export JOB_ID_MERGE=`sbatch --dependency=afterok:${JOB_ID_INDEX} $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_merge.sh $JOB_ID_INDEX|awk '{print $4}'`
echo MERGE $JOB_ID_MERGE

export JOB_ID_SPLIT=`sbatch --dependency=afterok:${JOB_ID_MERGE} $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_split.sh $JOB_ID_INDEX|awk '{print $4}'`
echo SPLIT $JOB_ID_SPLIT

export JOB_ID_HOPPER=`sbatch --dependency=afterok:${JOB_ID_SPLIT} $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_stage1.sh $SCRATCH/yb_lyso/${JOB_ID_MERGE}/out/ly99sim_all.mtz $SCRATCH/yb_lyso/${JOB_ID_SPLIT}_integ_exp_ref.txt|awk '{print $4}'`
echo HOPPER ${JOB_ID_HOPPER}

export JOB_ID_INTEGRATE=`sbatch --dependency=afterok:${JOB_ID_HOPPER} $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_predict.sh ${JOB_ID_HOPPER} | awk '{print $4}'`
echo INTEGRATE ${JOB_ID_INTEGRATE}

export JOB_ID_STAGE2=`sbatch --dependency=afterok:${JOB_ID_INTEGRATE} $MODULES/exafel_project/kpp-sim/yb_lyso/yb_lyso_100k_stage2.sh ${JOB_ID_INDEX} ${JOB_ID_MERGE} ${JOB_ID_INTEGRATE} | awk '{print $4}'`
echo STAGE2 ${JOB_ID_STAGE2}

```
<h3>Frequently asked questoins</h3>
Q. The simulation script does not work on Frontier, because the compute nodes cannot download the PDB file from the internet.

A. Replace the crystal section of the phil string as follows:

```
crystal {
  structure=pdb
  pdb.source=file
  pdb.file=/path_to_file/4bs7.pdb # Yb lysozyme, Celia Sauter(no relation), 1.7 Angstrom
  length_um=0.5 # increase crystal path length
}
```
To get the file, switch to a directory on Frontier (/path_to_file/) and type ```iotbx.fetch_pdb 4bs7```.
