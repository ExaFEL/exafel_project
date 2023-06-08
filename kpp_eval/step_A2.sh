#!/bin/bash -l
#SBATCH -N 8             # Number of nodes
#SBATCH -J ExaFEL_eA2    # Job title
#SBATCH -A m2859         # allocation
#SBATCH -C cpu           # cpu / gpu
#SBATCH -q regular       # regular queue
#SBATCH -t 00:30:00      # wall clock time limit
#SBATCH -o %j.out        # SLURM job stdout
#SBATCH -e %j.err        # SLURM job err

if [ -z "$SLURM_JOB_ID" ]; then export SLURM_JOB_ID="ExaFEL_eA2"; fi
export RESULTS_DIRECTORY=./$SLURM_JOB_ID
mkdir -p $RESULTS_DIRECTORY; cd $RESULTS_DIRECTORY || exit

INPUT_PATHS=''
for EXPT_PATH in "$STAGE1_JOB_PATH"/expers/rank*/ ; do
  INPUT_PATHS="${INPUT_PATHS}\n  path=$(realpath "$EXPT_PATH")"
done
for REFL_PATH in "$STAGE1_JOB_PATH"/refls/rank*/ ; do
  INPUT_PATHS="${INPUT_PATHS}\n  path=$(realpath "$REFL_PATH")"
done

echo -p "
dispatch.step_list = input balance substitute
input {$INPUT_PATHS
  reflections_suffix = refined_0.refl
  experiments_suffix = refined_0.expt
  persistent_refl_cols = shoebox
  persistent_refl_cols = bbox
  persistent_refl_cols = xyzcal.px
  persistent_refl_cols = xyzcal.mm
  persistent_refl_cols = xyzobs.px.value
  persistent_refl_cols = xyzobs.mm.value
  persistent_refl_cols = xyzobs.mm.variance
  persistent_refl_cols = delpsical.rad
  persistent_refl_cols = panel
  parallel_file_load.balance = global1 *global2 per_node
}
substitute {
  input = $DIALS_JOB_BATH/out/*refined.refl
  apply = False
}
output {
  prefix = strong_stage1
  output_dir = out/
  save_experiments_and_reflections = True
}
" > step_A2.phil

echo "job start $(date)"; pwd
srun -n 128 -c 16 cctbx.xfel.merge step_A2.phil
echo "job end $(date)"; pwd
