# Installation

Install using the these [instructions](installation.md). Note the specific branches that need to be checked out, including `nxmx_writer_experimental` for `cctbx_project`, and `experimental_high_remote` for `exafel_project`.

Create a working directory:
```
cd $WORK
mkdir exafel_output
cd exafel_output
```

# Image Simulation
Set an environment variable for the number of still shots to simulate, for example, for 100,000 still shots:
```
export NUM_SHOTS=100000
```

Run the image simulation script to simulate $NUM_SHOTS still shots of ferredoxin:
```
cd $WORK/exafel_output
sbatch --time=1:30:00 -A $NERSC_GPU_ALLOCATION $MODULES/exafel_project/kpp-sim/sim_ferredoxin_high_remote.sh $NUM_SHOTS
```
Images will be saved in `$SCRATCH/ferredoxin_sim/{JOB_ID_SIM}`, where `JOB_ID_SIM` is the job ID of the submitted job.

# Processing with DIALS

## Indexing and integration:

Run the indexing and integration script:
```
sbatch --time=1:30:00 -A $NERSC_CPU_ALLOCATION $MODULES/exafel_project/kpp-sim/ferredoxin_index_high_remote.sh {JOB_ID_SIM}
```
Output will be saved in `$SCRATCH/ferredoxin_sim/{JOB_ID_INDEX}`, where `JOB_ID_INDEX` is the job ID of the submitted job. A phil file will be saved as `$WORK/exafel_output/index.phil` and used later in diffBragg stage 1 integrate.

Visualize example indexed image:
```
cd $SCRATCH/ferredoxin_sim/{JOB_ID_INDEX}
dials.image_viewer idx-image_rank_00000_00000_indexed.refl idx-image_rank_00000_00000_refined.expt
```

Visualize example integrated image:
```
dials.image_viewer idx-image_rank_00000_00000_integrated.*
```

## Unit Cell Analysis
The file for unit cell analysis is output in `$SCRATCH/ferredoxin_sim/{JOB_ID_INDEX}/tdata_cells.tdata` from the indexing and integration script.

Start interactive session:
```
salloc -N 1 --time=60 -C gpu -A $NERSC_GPU_ALLOCATION --qos=interactive --ntasks-per-gpu=1
```

Reconfigure modules:
```
cd $MODULES
libtbx.configure LS49 ls49_big_data uc_metrics lunus sim_erice xfel_regression
libtbx.refresh
```

Go to working directory: 
```
cd $WORK/exafel_output
```

Run covariance analysis command:
```
uc_metrics.dbscan file_name=$SCRATCH/ferredoxin_sim/{JOB_ID_INDEX}/tdata_cells.tdata space_group=C12/m1 feature_vector=a,b,c eps=0.20 write_covariance=True metric=L2norm show_plot=True 
```

**Possible issue: Should the space group be C12/m1 or C121?**

This command outputs covariance file `covariance_tdata_cells.pickle` to the working directory `$WORK/exafel_output`.

## Conventional merging

Run the merging script:
```
cd $WORK/exafel_output
sbatch --time 00:10:00 -A $NERSC_CPU_ALLOCATION $MODULES/exafel_project/kpp-sim/ferredoxin_merge_high_remote.sh {JOB_ID_INDEX}
```
Output will be saved in `$SCRATCH/ferredoxin_sim/{JOB_ID_MERGE}`, where `JOB_ID_MERGE` is the job ID of the submitted job.

# diffBragg Stage 1

## Step 1: make_input_file

Organize the output of indexing:
```
cd $WORK/exafel_output
diffBragg.make_input_file $SCRATCH/ferredoxin_sim/{JOB_ID_INDEX} exp_ref_spec
```

## Step 2: hopper

Run the hopper script:
```
cd $WORK/exafel_output
sbatch --time 01:30:00 -A $NERSC_GPU_ALLOCATION $MODULES/exafel_project/kpp-sim/slurm_hopper_stage1_kokkos.sh $SCRATCH/ferredoxin_sim/{JOB_ID_MERGE}/out/ly99sim_all.mtz exp_ref_spec_file=$WORK/exafel_output/exp_ref_spec
```
Output will be saved in `$SCRATCH/ferredoxin_sim/{JOB_ID_HOPPER}/hopper_stage_one`, where `JOB_ID_HOPPER` is the job ID of the submitted job.

Visualize an example result:
```
cd $SCRATCH/ferredoxin_sim/{JOB_ID_HOPPER}/hopper_stage_one
dials.image_viewer expers/rank0/stage1_idx-image_rank_00000_00000_refined_00000.expt refls/rank0/stage1_idx-image_rank_00000_00000_refined_00000.refl
```

Generate histogram to evaluate the mismatch between the predicted and observed reflection centroids:
```
cd $SCRATCH/ferredoxin_sim/{JOB_ID_HOPPER}/hopper_stage_one
diffBragg.pred_offsets "refls/rank*/*.refl"
```
We aim for the mismatch to be less than a pixel.

## Step 3: integrate

Run the integrate script:
```
cd $WORK/exafel_output
sbatch --time 01:30:00 -A $NERSC_GPU_ALLOCATION $MODULES/exafel_project/kpp-sim/slurm_integrate_stage1_kokkos.sh {JOB_ID_HOPPER}
```
Output will be saved in `$SCRATCH/ferredoxin_sim/{JOB_ID_INTEGRATE}`, where `JOB_ID_INTEGRATE` is the job ID of the submitted job.

View an example result in dials.image_viewer:
```
cd $SCRATCH/ferredoxin_sim/{JOB_ID_INTEGRATE}/out
dials.image_viewer stage1_idx-image_rank_00000_00000_refined_00000_00000_predicted.*
```

View an example result in dials.reflection_viewer:
```
dials.reflection_viewer stage1_idx-image_rank_00000_00000_refined_00000_00000_predicted.refl
```

# diffBragg Stage 2

Edit output from diffBragg stage 1 integrate and create a 2-shot and 10-shot example for testing:
```
cd $SCRATCH/ferredoxin_sim/{JOB_ID_INTEGRATE}/out
libtbx.python

# in Python shell
import pandas
df = pandas.read_pickle("preds_for_hopper.pkl")
df = df.rename(columns={'predicted_refls': 'predictions'})
df.to_pickle("preds_for_hopper.pkl")

# Create 2-shot example
df2 = df.iloc[:2]
df2.to_pickle("2.pkl")

# Create 10-shot example
df2 = df.iloc[:10]
df2.to_pickle("10.pkl")

# Create a 10k-shot example
df2 = df.iloc[:10000]
df2.to_pickle("10k.pkl")

quit()
```

## Testing a small example

Start an interactive session:
```
salloc -N 1 --time=60 -C gpu -A $NERSC_GPU_ALLOCATION --qos=interactive --ntasks-per-gpu=1
cd $WORK/exafel_output
```

Test the 2-shot example:
```
simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/hopper_stage1_kokkos_diff.phil io.output_dir=tests pandas_table=$SCRATCH/ferredoxin_sim/{JOB_ID_INTEGRATE}/out/2.pkl num_devices=1
```

Test the 10-shot example:
```
simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/hopper_stage1_kokkos_diff.phil io.output_dir=tests pandas_table=$SCRATCH/ferredoxin_sim/{JOB_ID_INTEGRATE}/out/10.pkl num_devices=1
```

The output structure factors can be analyzed with the following script:
```
cd $WORK/exafel_output/tests
libtbx.python $MODULES/exafel_project/kpp_utils/convert_npz_to_mtz.py
```

Run the stage 2 script with 10,000 still shots:
<mark>Running with >10,000 shots causes an OOM error.</mark>
```
sbatch --time 01:30:00 -A $NERSC_GPU_ALLOCATION $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh {JOB_ID_INTEGRATE} 10k {JOB_ID_MERGE}
```
Results are saved in `$WORK/diffbragg_stage2/{JOB_ID_STAGE2}`, where `JOB_ID_STAGE2` is the job ID of the submitted job.

Analyze the Pearson correlation coefficient between the ground truth and predicted structure factors, starting from the output of conventional merging with DIALS:
```
cd $WORK/exafel_output/{JOB_ID_STAGE2}
export JOB_ID_STAGE2={JOB_ID_STAGE2}
export JOB_ID_MERGE={JOB_ID_MERGE}
libtbx.python $MODULES/exafel_project/kpp_utils/convert_npz_to_mtz.py
```

# Example Processing Results

## 10 still shots of ferredoxin

**TODO with instructions above, all times above are listed for 100,000 shots, adjust time accordingly for 10 still shots, erring on the generous side because there may be some fixed amount of setup time. The entire pipeline for 10 shots could be run on an interactive node, no need to submit jobs.**

JOB_ID_SIM =

JOB_ID_INDEX =

JOB_ID_MERGE =

JOB_ID_HOPPER =

JOB_ID_INTEGRATE =

JOB_ID_STAGE2 =


## 10,000 still shots of ferredoxin

**TODO with instructions above, all times above are listed for 100,000 shots, adjust time accordingly for 10,000 still shots, erring on the generous side because there may be some fixed amount of setup time.**

JOB_ID_SIM =

JOB_ID_INDEX =

JOB_ID_MERGE =

JOB_ID_HOPPER =

JOB_ID_INTEGRATE =

JOB_ID_STAGE2 =


## 100,000 still shots of ferredoxin

See [notes](notes.txt) for notes on previous processing of 100,000 still shots; those notes do not follow the instructions above exactly.

**TODO with instructions above**

JOB_ID_SIM =

JOB_ID_INDEX =

JOB_ID_MERGE =

JOB_ID_HOPPER =

JOB_ID_INTEGRATE =

JOB_ID_STAGE2 =


