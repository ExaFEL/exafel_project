Image simulation of ferredoxin high remote, Nick's new script:

exafel_project
branch: experimental_high_remote

> cd $WORK/exafel_output
> sbatch $MODULES/exafel_project/kpp-sim/sim_ferredoxin_high_remote.sh
Submitted batch job 9287607
SUCCESS

Images are saved in $SCRATCH/ferredoxin_sim/9287607

Indexing/integration/unit cell analysis:

> sbatch $MODULES/exafel_project/kpp-sim/ferredoxin_index_9287607.sh
Submitted batch job 9398750
SUCCESS

Visualize images:

> cd $SCRATCH/ferredoxin_sim/9398750
> dials.image_viewer idx-image_rank_00122_00065_indexed.refl idx-image_rank_00122_00065_refined.expt
> dials.image_viewer idx-image_rank_00122_00065_integrated.*

File for unit Cell analysis:
$SCRATCH/ferredoxin_sim/9398750/tdata_cells.tdata


Unit Cell analysis:

Start interactive session:
salloc -N 1 --time=60 -C gpu -A m3562_g --qos=interactive --ntasks-per-gpu=1


> cd  $MODULES
> libtbx.configure LS49 ls49_big_data uc_metrics lunus sim_erice xfel_regression
> libtbx.refresh


Go to working directory: $WORK/exafel_output

Run covariance analysis command:
uc_metrics.dbscan file_name=$SCRATCH/ferredoxin_sim/9398750/tdata_cells.tdata space_group=C12/m1 feature_vector=a,b,c eps=0.20 write_covariance=5991038.tt metric=L2norm show_plot=True 

Outputs covariance file in working directory $WORK/exafel_output: covariance_tdata_cells.pickle


Conventional merging:
> cd $WORK/exafel_output
> sbatch $MODULES/exafel_project/kpp-sim/ferredoxin_merge_9398750.sh
9521300
SUCCESS

output in:
$SCRATCH/ferredoxin_sim/9521300


Conventional merging 10K:


DiffBragg stage 1:

Step 1: (input is output of indexing)
> cd $WORK/diffbragg_stage1/high_remote
> diffBragg.make_input_file $SCRATCH/ferredoxin_sim/9398750 exp_ref_spec

Step 2: Hopper

> cd $WORK/diffbragg_stage1/high_remote
> sbatch $MODULES/exafel_project/kpp-sim/slurm_hopper_stage1_kokkos.sh
Submitted batch job 9687486
TIME OUT

3 hour and 36 min script:
> cd $WORK/diffbragg_stage1/high_remote
> sbatch $MODULES/exafel_project/kpp-sim/slurm_hopper_stage1_kokkos.sh
Submitted batch job 9689612
jobstart Tue 30 May 2023 05:23:18 AM PDT
jobend Tue 30 May 2023 06:24:08 AM PDT
SUCCESS

results in $SCRATCH/ferredoxin_sim/9689612/hopper_stage_one


###
View results:
> cd $SCRATCH/ferredoxin_sim/9689612/hopper_stage_one
> dials.image_viewer expers/rank0/stage1_idx-image_rank_01002_00062_refined_75520.expt refls/rank0/stage1_idx-image_rank_01002_00062_refined_75520.refl

> dials.image_viewer expers/rank0/stage1_idx-image_rank_01020_00079_refined_41728.expt refls/rank0/stage1_idx-image_rank_01020_00079_refined_41728.refl

Generate histogram:
> cd $SCRATCH/ferredoxin_sim/9689612/hopper_stage_one
> diffBragg.pred_offsets "refls/rank*/*.refl"


Step 3: Integrate
> cd $WORK/diffbragg_stage1/high_remote
> sbatch $MODULES/exafel_project/kpp-sim/slurm_integrate_stage1_kokkos.sh
Submitted batch job 9713113
jobstart Tue 30 May 2023 03:21:25 PM PDT
jobend Tue 30 May 2023 04:16:38 PM PDT
SUCCESS

results in $SCRATCH/ferredoxin_sim/9713113

View results:
> cd $SCRATCH/ferredoxin_sim/9713113/out
> dials.image_viewer stage1_idx-image_rank_00098_00086_refined_25164_10350_predicted.*

> dials.reflection_viewer stage1_idx-image_rank_00098_00086_refined_25164_10350_predicted.refl
We should be seeing noise, but seeing zeros


> dials.image_viewer stage1_idx-image_rank_00098_00087_refined_10024_48452_integrated.*


DiffBragg Stage 2:
on cctbx_project branch nxmx_writer_experimental
########################################
Testing that it works with small example:
> cd $SCRATCH/ferredoxin_sim/9713113/out
> libtbx.python

import pandas
df = pandas.read_pickle("preds_for_hopper.pkl")
df = df.rename(columns={'predicted_refls': 'predictions'})
df2 = df.iloc[:2]


df2 = df.iloc[:10]
df2.to_pickle("10.pkl")

quit()

> salloc -N 1 --time=60 -C gpu -A m3562_g --qos=interactive --ntasks-per-gpu=1
> cd $WORK/diffbragg_stage2
> simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/diffBragg_stage2.phil io.output_dir=tests pandas_table=$SCRATCH/ferredoxin_sim/9713113/out/2.pkl num_devices=1 logfiles=True profile=True prep_time=1 logging.disable=False max_calls=[501] save_model_freq=10 refiner.load_data_from_refl=False refiner.reference_geom=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt structure_factors.mtz_name=$SCRATCH/ferredoxin_sim/9521300/out/ly99sim_all.mtz structure_factors.mtz_column="Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)" min_multiplicity=1 refine_spot_scale=[0]

Can add to check structure factors are refining:
refine_spot_scale=[0]


> simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/diffBragg_stage2.phil io.output_dir=tests pandas_table=$SCRATCH/ferredoxin_sim/9713113/out/2a.pkl num_devices=1 logfiles=True profile=True prep_time=1 logging.disable=False max_calls=[501] save_model_freq=10 refiner.load_data_from_refl=False refiner.reference_geom=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt structure_factors.mtz_name=$SCRATCH/ferredoxin_sim/9521300/out/ly99sim_all.mtz structure_factors.mtz_column="Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)" min_multiplicity=1 refine_spot_scale=[1]



simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/hopper_stage1_kokkos_diff.phil io.output_dir=tests pandas_table=$SCRATCH/ferredoxin_sim/9713113/out/2.pkl num_devices=1

simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/hopper_stage1_kokkos_diff.phil io.output_dir=tests pandas_table=$SCRATCH/ferredoxin_sim/9713113/out/2a.pkl num_devices=1

small test, 10 shot:
> simtbx.diffBragg.stage_two $MODULES/exafel_project/kpp-sim/diffBragg_stage2.phil io.output_dir=tests pandas_table=$SCRATCH/ferredoxin_sim/9713113/out/10.pkl num_devices=1 logfiles=True profile=True prep_time=1 logging.disable=False max_calls=[501] save_model_freq=50 refiner.load_data_from_refl=False refiner.reference_geom=$MODULES/exafel_project/kpp-sim/t000_rg002_chunk000_reintegrated_000000.expt structure_factors.mtz_name=$SCRATCH/ferredoxin_sim/9521300/out/ly99sim_all.mtz structure_factors.mtz_column="Iobs(+),SIGIobs(+),Iobs(-),SIGIobs(-)" min_multiplicity=1

########################################

Actual stage 2 script:

> cd $SCRATCH/ferredoxin_sim/9713113/out
> libtbx.python

import pandas
df = pandas.read_pickle("preds_for_hopper.pkl")
df = df.rename(columns={'predicted_refls': 'predictions'})
df.to_pickle("preds_for_hopper.pkl")
quit()


> cd $WORK/diffbragg_stage2
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh
Submitted batch job 10209111
OUT OF MEMORY

> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh (halved the # of total ranks)
Submitted batch job 10210943
OUT OF MEMORY

Back to normal ranks:

CUT LIST to 10k:
> cd $SCRATCH/ferredoxin_sim/9713113/out
> libtbx.python

import pandas
df = pandas.read_pickle("preds_for_hopper.pkl")
df2 = df.iloc[:10000]
df2.to_pickle("10k.pkl")

quit()

> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh (switched to 10k.pkl)
Submitted batch job 10211797
SUCCESS
Results in $WORK/diffbragg_stage2/10211797
Analyze me!

> cd $WORK/diffbragg_stage2/10211797
> libtbx.python $MODULES/exafel_project/kpp_utils/convert_npz_to_mtz.py

Make lists 20k, 30k, etc to 90K and run:

> cd $SCRATCH/ferredoxin_sim/9713113/out
> libtbx.python

import pandas
df = pandas.read_pickle("preds_for_hopper.pkl")

for i in range(1,10):
	df2 = df.iloc[:i*10000]
	df2.to_pickle(str(i*10) + "k.pkl")

quit()


Run all:

> cd $WORK/diffbragg_stage2
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh 10k
10217122
SUCCESS
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh 20k
10217123
TIMEOUT
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh 30k
10217124
TIMEOUT
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh 40k
10217125
OOM
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh 50k
10217126
OOM
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh 60k
10217127
OOM
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh 70k
10217128
OOM
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh 80k
10217129
OOM
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh 90k
10217130
OOM
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh preds_for_hopper
10217132
OOM


Re-running with flag refiner.stage_two.use_nominal_hkl = False:
> cd $WORK/diffbragg_stage2
> sbatch $MODULES/exafel_project/kpp-sim/diffBragg_stage2.sh 10k
Submitted batch job 10508234
FINISHED

########################################
Useful links:
https://github.com/cctbx/cctbx_project/blob/nxmx_writer/simtbx/command_line/hopper_ensemble.py
https://github.com/cctbx/cctbx_project/blob/nxmx_writer/simtbx/diffBragg/phil.py

DiffBragg Stage 2 --> ens.hopper (ens.hopper is supposed to replace diffbragg stage2):
Testing that it works with small example:
> cd $SCRATCH/ferredoxin_sim/9713113/out
>libtbx.python

import pandas
df = pandas.read_pickle("preds_for_hopper.pkl")
df = df.rename(columns={'predicted_refls': 'predictions'})
df2 = df.iloc[:2]
df2.to_pickle("2.pkl")
quit()

> salloc -N 1 --time=60 -C gpu -A m3562_g --qos=interactive --ntasks-per-gpu=2
> cd $WORK/diffbragg_stage2
ens.hopper $SCRATCH/ferredoxin_sim/9713113/out/2.pkl $MODULES/exafel_project/kpp-sim/ens_hopper.phil --outdir preimport --maxSigma 3 --saveFreq 10  --preImport --refl predictions

ens.hopper preimport/preImport_for_ensemble.pkl $MODULES/exafel_project/kpp-sim/ens_hopper.phil --outdir global --maxSigma 3 --saveFreq 10 --refl ens.hopper.imported --cmdlinePhil fix.Nabc=True fix.ucell=True fix.RotXYZ=True fix.Fhkl=False fix.G=False sigmas.G=1e-2

##
Redo with 10 examples:
Testing that it works with small example:
> cd $SCRATCH/ferredoxin_sim/9713113/out
> libtbx.python

import pandas
df = pandas.read_pickle("preds_for_hopper.pkl")
df = df.rename(columns={'predicted_refls': 'predictions'})
df2 = df.iloc[:10]
df2.to_pickle("10.pkl")
quit()

> salloc -N 1 --time=60 -C gpu -A m3562_g --qos=interactive --ntasks-per-gpu=2
> cd $WORK/diffbragg_stage2
ens.hopper $SCRATCH/ferredoxin_sim/9713113/out/10.pkl $MODULES/exafel_project/kpp-sim/ens_hopper.phil --outdir preimport --maxSigma 3 --saveFreq 10 --preImport --refl predictions


ens.hopper preimport/preImport_for_ensemble.pkl $MODULES/exafel_project/kpp-sim/ens_hopper.phil --outdir global --maxSigma 3 --saveFreq 10 --refl ens.hopper.imported --cmdlinePhil fix.Nabc=True fix.ucell=True fix.RotXYZ=True fix.Fhkl=False fix.G=False sigmas.G=1e-2

###########
Stage 2 cytochrome:

Check that gradients of the structure factors are nonzero:

> cd $MODULES/diffbragg_benchmarks/AD_SE_13_222
> simtbx.diffBragg.stage_two data_222.phil  io.output_dir=tests pandas_table=2.pkl num_devices=1 logfiles=True profile=True prep_time=1 logging.disable=False max_calls=[501] save_model_freq=250 refiner.load_data_from_refl=True refiner.reference_geom=data_222/Jungfrau_model.json structure_factors.mtz_name=100shuff.mtz structure_factors.mtz_column="F(+),SIGF(+),F(-),SIGF(-)" min_multiplicity=1 refine_spot_scale=[0]


###########

Rules of thumb:

Perlmutter CPU: 256 * -N = -c * -n
Perlmutter GPU: 128 * -N = -c * -n
