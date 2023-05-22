# Installation

Install using the these [instructions](installation.md). Note the specific branches that need to be checked out, including `nxmx_writer_experimental` for `cctbx_project`.

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
Images will be saved in `$SCRATCH/ferredoxin_sim/{JOB_ID_SIM}`, where `{JOB_ID_SIM}` is the job ID of the submitted job.

Set an environment variable for JOB_ID_SIM:
```
export JOB_ID_SIM={JOB_ID_SIM}
```

To view an example image:
```
cd $SCRATCH/ferredoxin_sim/$JOB_ID_SIM
dials.image_viewer image_rank_00000.h5
```

# Processing with DIALS

## Indexing and integration:

Run the indexing and integration script:
```
sbatch --time=1:30:00 -A $NERSC_CPU_ALLOCATION $MODULES/exafel_project/kpp-sim/ferredoxin_index_high_remote.sh $JOB_ID_SIM
```
Output will be saved in `$SCRATCH/ferredoxin_sim/{JOB_ID_INDEX}`, where `JOB_ID_INDEX` is the job ID of the submitted job. 

Set an environment variable for JOB_ID_INDEX:
```
export JOB_ID_INDEX={JOB_ID_INDEX}
```

A phil file will be saved as `$SCRATCH/ferredoxin_sim/$JOB_ID_INDEX/index.phil` and used later in diffBragg stage 1 integrate.

Visualize example indexed image:
```
cd $SCRATCH/ferredoxin_sim/$JOB_ID_INDEX
dials.image_viewer idx-image_rank_00000_refined.expt idx-image_rank_00000_indexed.refl 
```

Visualize example integrated image:
```
dials.image_viewer idx-image_rank_00000_integrated.*
```

## Unit Cell Analysis
The file for unit cell analysis is output in `$SCRATCH/ferredoxin_sim/$JOB_ID_INDEX/tdata_cells.tdata` from the indexing and integration script.

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
uc_metrics.dbscan file_name=$SCRATCH/ferredoxin_sim/$JOB_ID_INDEX/tdata_cells.tdata space_group=C12/m1 feature_vector=a,b,c eps=0.20 write_covariance=True metric=L2norm show_plot=True 
```

This command outputs covariance file `covariance_tdata_cells.pickle` to the working directory `$WORK/exafel_output`.

## Conventional merging

Run the merging script:
```
cd $WORK/exafel_output
sbatch --time 00:10:00 -A $NERSC_CPU_ALLOCATION $MODULES/exafel_project/kpp-sim/ferredoxin_merge_high_remote.sh $JOB_ID_INDEX
```
Output will be saved in `$SCRATCH/ferredoxin_sim/{JOB_ID_MERGE}`, where `JOB_ID_MERGE` is the job ID of the submitted job.

Set an environment variable for JOB_ID_MERGE:
```
export JOB_ID_MERGE={JOB_ID_MERGE}
```

There should be a file called `ly99sim_all.mtz` in `$SCRATCH/ferredoxin_sim/{JOB_ID_MERGE}/out`.

# diffBragg Stage 1

## Step 1: make_input_file

Organize the output of indexing:
```
cd $WORK/exafel_output
diffBragg.make_input_file $SCRATCH/ferredoxin_sim/$JOB_ID_INDEX exp_ref_spec
```
This command results in a file `exp_ref_spec` in the working directory `$WORK/exafel_output`.

## Step 2: hopper

Run the hopper script:
```
cd $WORK/exafel_output
sbatch --time 01:30:00 -A $NERSC_GPU_ALLOCATION $MODULES/exafel_project/kpp-sim/slurm_hopper_stage1_kokkos.sh $SCRATCH/ferredoxin_sim/$JOB_ID_MERGE/out/ly99sim_all.mtz $WORK/exafel_output/exp_ref_spec
```
Output will be saved in `$SCRATCH/ferredoxin_sim/{JOB_ID_HOPPER}/hopper_stage_one`, where `JOB_ID_HOPPER` is the job ID of the submitted job.

Set an environment variable for JOB_ID_HOPPER:
```
export JOB_ID_HOPPER={JOB_ID_HOPPER}
```

Visualize an example result:
```
cd $SCRATCH/ferredoxin_sim/$JOB_ID_HOPPER/hopper_stage_one
dials.image_viewer expers/rank0/stage1_idx-image_rank_00000_00000_refined_00000.expt refls/rank0/stage1_idx-image_rank_00000_00000_refined_00000.refl
```

Generate histogram to evaluate the mismatch between the predicted and observed reflection centroids:
```
cd $SCRATCH/ferredoxin_sim/$JOB_ID_HOPPER/hopper_stage_one
diffBragg.pred_offsets "refls/rank*/*.refl"
```
We aim for the mismatch to be less than a pixel.

## Step 3: integrate

Run the integrate script:
```
cd $WORK/exafel_output
sbatch --time 01:30:00 -A $NERSC_GPU_ALLOCATION $MODULES/exafel_project/kpp-sim/slurm_integrate_stage1_kokkos.sh $JOB_ID_INDEX $JOB_ID_HOPPER
```
Output will be saved in `$SCRATCH/ferredoxin_sim/{JOB_ID_INTEGRATE}`, where `JOB_ID_INTEGRATE` is the job ID of the submitted job.

Set an environment variable for JOB_ID_INTEGRATE:
```
export JOB_ID_INTEGRATE={JOB_ID_INTEGRATE}
```

View an example result in dials.image_viewer:
```
cd $SCRATCH/ferredoxin_sim/$JOB_ID_INTEGRATE/out
dials.image_viewer stage1_idx-image_rank_00000_00000_refined_00000_00000_predicted.*
```

View an example result in dials.reflection_viewer:
```
dials.reflection_viewer stage1_idx-image_rank_00000_00000_refined_00000_00000_predicted.refl
```

# diffBragg Stage 2

Edit output from diffBragg stage 1 integrate and create a 2-shot and 10-shot example for testing:
```
cd $SCRATCH/ferredoxin_sim/$JOB_ID_INTEGRATE/out
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
simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/hopper_stage1_kokkos_diff.phil io.output_dir=tests pandas_table=$SCRATCH/ferredoxin_sim/$JOB_ID_INTEGRATE/out/2.pkl num_devices=1 exp_ref_spec_file=$WORK/exafel_output/exp_ref_spec structure_factors.mtz_name=$SCRATCH/ferredoxin_sim/$JOB_ID_MERGE/out/ly99sim_all.mtz refiner.reference_geom=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
```

Test the 10-shot example:
```
simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/hopper_stage1_kokkos_diff.phil io.output_dir=tests pandas_table=$SCRATCH/ferredoxin_sim/$JOB_ID_INTEGRATE/out/10.pkl num_devices=1 exp_ref_spec_file=$WORK/exafel_output/exp_ref_spec structure_factors.mtz_name=$SCRATCH/ferredoxin_sim/$JOB_ID_MERGE/out/ly99sim_all.mtz refiner.reference_geom=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
```

The output structure factors can be analyzed with the following script:
```
cd $WORK/exafel_output/tests
export JOB_ID_STAGE2=tests
libtbx.python $MODULES/exafel_project/kpp_utils/evaluate_stage_two.py
```

## Testing 10,000 still shots

Run the stage 2 script with 10,000 still shots:
```
sbatch --time 01:30:00 -A $NERSC_GPU_ALLOCATION $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh $JOB_ID_INTEGRATE 10k $JOB_ID_MERGE
```
Results are saved in `$WORK/diffbragg_stage2/{JOB_ID_STAGE2_10k}`, where `JOB_ID_STAGE2_10k` is the job ID of the submitted job.

Analyze the Pearson correlation coefficient between the ground truth and predicted structure factors, starting from the output of conventional merging with DIALS:
```
export JOB_ID_STAGE2={JOB_ID_STAGE2_10k}
export JOB_ID_MERGE={JOB_ID_MERGE}
cd $WORK/exafel_output/$JOB_ID_STAGE2
libtbx.python $MODULES/exafel_project/kpp_utils/evaluate_stage_two.py
```

## Processing all still shots

Run the stage 2 script with all still shots:
```
sbatch --time 01:30:00 -A $NERSC_GPU_ALLOCATION $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh $JOB_ID_INTEGRATE preds_for_hopper $JOB_ID_MERGE
```
Results are saved in `$WORK/diffbragg_stage2/{JOB_ID_STAGE2}`, where `JOB_ID_STAGE2` is the job ID of the submitted job.

Analyze the Pearson correlation coefficient between the ground truth and predicted structure factors, starting from the output of conventional merging with DIALS:
```
export JOB_ID_STAGE2={JOB_ID_STAGE2}
export JOB_ID_MERGE={JOB_ID_MERGE}
cd $WORK/exafel_output/$JOB_ID_STAGE2
libtbx.python $MODULES/exafel_project/kpp_utils/evaluate_stage_two.py
```

# Example Processing Results

## 1024 still shots of ferredoxin

$SCRATCH is /pscratch/sd/v/vidyagan

$WORK is /global/cfs/cdirs/m3562/users/vidyagan/p20231

JOB_ID_SIM = 10729219

JOB_ID_INDEX = 10731329

JOB_ID_MERGE = 10750362

JOB_ID_HOPPER = 10776453

JOB_ID_INTEGRATE = 10780371

### diffBragg stage 2 processing
Start an interactive node:
```
salloc -N 4 --time=240 -C gpu -A $NERSC_GPU_ALLOCATION --qos=interactive --ntasks-per-node=8 --cpus-per-gpu=2 --gpus-per-node=4
```

Export the following environment variables:
```
export JOB_ID_MERGE=10750362
export JOB_ID_INTEGRATE=10780371
export PKL_FILE=preds_for_hopper

export PERL_NDEV=4  # number GPU per node
export PANDA=$SCRATCH/ferredoxin_sim/$JOB_ID_INTEGRATE/out/${PKL_FILE}.pkl
export GEOM=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt
export IBV_FORK_SAFE=1
export RDMAV_HUGEPAGES_SAFE=1
export DIFFBRAGG_USE_KOKKOS=1
export MPI4PY_RC_RECV_MPROBE=False
```

Run the following:
```
srun --cpus-per-task=16 -N 4 --ntasks-per-node=8 --cpus-per-gpu=32 --gpus-per-node=4 simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/hopper_stage1_kokkos_diff.phil io.output_dir=$SLURM_JOB_ID pandas_table=$PANDA num_devices=4 exp_ref_spec_file=$WORK/exafel_output/exp_ref_spec structure_factors.mtz_name=$SCRATCH/ferredoxin_sim/$JOB_ID_MERGE/out/ly99sim_all.mtz refiner.reference_geom=$GEOM logfiles=true
```

## 20,000 still shots of ferredoxin

$SCRATCH is /pscratch/sd/v/vidyagan

$WORK is /global/cfs/cdirs/m3562/users/vidyagan/p20231

JOB_ID_SIM = 10747031

JOB_ID_INDEX = 10777319

JOB_ID_MERGE = 10779262

JOB_ID_HOPPER = 10780908

JOB_ID_INTEGRATE = 10786274

JOB_ID_STAGE2 = 11161559


|                            | walltime | nodes | ranks | node type | inodes | disk space |
| -------------------------- | -------- | ----- | ----- | --------- | ------ | ---------- |
| Image Creation             | 19:23    | 32    | 1024  | gpu       | 3073   | 356G       |
| DIALS indexing/integration | 20:16    | 8     | 256   | cpu       | 102041 | 38G        |
| DIALS merging              | 01:19    | 8     | 256   | cpu       | 1285   | 156M       |
| diffBragg hopper           | 12:32    | 32    | 256   | gpu       | 139988 | 15G        |
| diffBragg integrate        | 11:51    | 32    | 256   | gpu       | 79998  | 54G        |
| diffBragg stage 2          | 04:48    | 32    | 256   | gpu       | 20031  | 17G        |

## 100,000 still shots of ferredoxin

See [notes](notes.txt) for notes on previous processing of 100,000 still shots; those notes do not follow the instructions above exactly. In the processing of 100,000 still shots, diffBragg stage 2 was only successful for 10,000 still shots, 20,000 shots and above had an OOM error.

