#! /bin/bash
# Use a bash function to submit batch jobs that will run only
# after successful completion of the preceding job

chained_sbatch() {
	script=$1
	dependency=$2
	shift; shift # drop first two args from buffer
        args=$@

	if [ "$dependency" == "FAILED" ]; then
		# dependent on a job that was not sucessfully submitted
		echo "FAILED"
		return 1
	elif [ "$dependency" == "None" ]; then
		# not dependent on preceding jobs
		submitted_msg=$(sbatch $script $args)
	else
		# dependent on an existing queued job
		submitted_msg=$(sbatch --dependency=afterok:$dependency $script $args)
	fi
	if [ "$submitted_msg" == "" ]; then
		echo "FAILED"
		return 1
	else
		# print just the jobid
		echo $submitted_msg | awk '{ print $4 }'
	fi
}

export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
#export SCRIPTS=$MODULES/exafel_project/kpp-frontier/thermolysin
export SCRIPTS=$SCRATCH/thermolysin

# Simulate 130k images. No dependencies.
JOB_ID_SIM=$(chained_sbatch $SCRIPTS/thermolysin_test_sim.sh None)

# Index and integrate simulated images with dials.stills_process,
# pending completion of image simulation. Note the first argument
# is the dependency recognized by SLURM, and any remaining are
# arguments passed to the thermolysin_test_*.sh script.
JOB_ID_INDEX=$(chained_sbatch $SCRIPTS/thermolysin_test_index.sh $JOB_ID_SIM $JOB_ID_SIM)

# Merge stills processing results, pending completion of stills_process
JOB_ID_MERGE=$(chained_sbatch $SCRIPTS/thermolysin_test_merge.sh $JOB_ID_INDEX $JOB_ID_INDEX)

# Split results of stills processing and prepare file list for diffBragg.
JOB_ID_SPLIT=$(chained_sbatch $SCRIPTS/thermolysin_test_split.sh $JOB_ID_INDEX $JOB_ID_INDEX)

# Run diffBragg stage 1 ("hopper", local to each image).
# Depends on stills process and merging results. Note
# syntax bundling multiple jobids in the dependency argument.
JOB_ID_HOPPER=$(chained_sbatch $SCRIPTS/thermolysin_test_stage1.sh "${JOB_ID_SPLIT}:${JOB_ID_MERGE}" $JOB_ID_SPLIT $JOB_ID_MERGE)

# Complete spot prediction and interation of predictions with newly refined models.
JOB_ID_PREDICT=$(chained_sbatch $SCRIPTS/thermolysin_test_predict.sh $JOB_ID_HOPPER $JOB_ID_HOPPER)

# Run diffBragg stage 2 (global refinement of structure
# factors against pixel data) on integration results.
JOB_ID_STAGE2=$(chained_sbatch $SCRIPTS/thermolysin_test_stage2.sh $JOB_ID_PREDICT $JOB_ID_INDEX $JOB_ID_MERGE $JOB_ID_PREDICT)

echo "Job IDs to be executed sequentially:"
echo "$JOB_ID_SIM image simulation"
echo "$JOB_ID_INDEX stills_process (with postprocessing)"
echo "$JOB_ID_MERGE xfel.merge (with postprocessing)"
echo "$JOB_ID_SPLIT split stills processing results"
echo "$JOB_ID_HOPPER diffBragg stage 1 (hopper, local)"
echo "$JOB_ID_PREDICT prediction (diffBragg.integrate)"
echo "$JOB_ID_STAGE2 diffBragg stage 2 (global)"

