# Reservation 02, 12.5% scale toward KPPs for diffBragg stage 2 on Frontier

## Reservation 02 workflow and commands:

In this trial we will run stage 2 on 10 datasets, each using 64 nodes to process 131k images. The datasets will be 5 Yb lyso datasets of varying crystal sizes and 5 cytochrome datasets of varying crystal sizes.

### Environment setup

```
# ensure files and dirs created here can be r/w/x by others in the group
umask 002

# set global environment variables
export SCRATCH=/lustre/orion/chm137/proj-shared/cctbx
export RESERVATION_NAME=chm137

# track results under the reservation02 subdir
cd $SCRATCH/reservation02

# finally, ensure $MODULES is a valid path containing the exafel_project repo
```

### Submitting jobs

For cytochrome (crystal sizes 40, 25, 10, 5, 2 micron):
```
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cytochrome_131k_stage2.sh 1426077 1427767 1435064
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cytochrome_131k_stage2.sh 1429648 1429661 1434948
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cytochrome_131k_stage2.sh 1427782 1427786 1435065
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cytochrome_131k_stage2.sh 1427783 1427787 1435069
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cytochrome_131k_stage2.sh 1429649 1429662 1435711
```

For lysozyme (crystal sizes 2, 1, 0.5, 0.25, 0.125 micron):
```
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/yb_lyso_131k_stage2.sh 1427014 1427835 1428320
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/yb_lyso_131k_stage2.sh 1427017 1427900 1428322
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/yb_lyso_131k_stage2.sh 1411658 1427901 1428333
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/yb_lyso_131k_stage2.sh 1427020 1427902 1428365
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/yb_lyso_131k_stage2.sh 1427035 1427903 1428853
```

For Cry11Ba, 16.0 micron:
```
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cry11ba_500k_stage2.sh 1429675 1429811 1437715
```

For thermolysin, 0.5 micron:
```
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/thermolysin_500k_stage2.sh 1432661 1434903 1437231
```



### Analysis, begin with c.c. plot
```
S2JID=1439099; MRGJID=1429811; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/cry11ba/${MRGJID}/out/cry11ba_500k_all.mtz stage2=$SCRATCH/cry11ba/${S2JID}/${S2JID} pdb=${MODULES}/exafel_project/kpp-sim/cry11ba/7qyd.pdb n_bins=10 stat=cc_anom
```

## copied from README in the scratch dir: 12.5 % scale trials for the KPP

### advance testing prior to the day
1443526: cytochrome, 131k, 64 nodes, 20.0 micron
1443527: Yb lysozyme, 131k, 64 nodes, 2.0 micron

1444496: cry11ba, 524k, 256 nodes, 16 micron
1444501: thermolysin, 524k, 256 nodes, 0.5 micron
1445035: thermolysin

#### thermolysin:
```
S2JID=1444501; MRGJID=1434903; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/thermolysin/${MRGJID}/out/ly99sim_all.mtz stage2=$SCRATCH/reservation02/${S2JID}/${S2JID} pdb=${MODULES}/exafel_project/kpp-sim/thermolysin/4tnl.pdb n_bins=10 stat=cc_anom
```

#### cry11ba:
60 min timeout, 282 iterations OK
```
S2JID=1444496; MRGJID=1429811; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/cry11ba/${MRGJID}/out/cry11ba_500k_all.mtz stage2=$SCRATCH/reservation02/${S2JID}/${S2JID} pdb=${MODULES}/exafel_project/kpp-sim/cry11ba/7qyd.pdb n_bins=10 stat=cc_anom
```

### continuing day-of:

#### cytochrome runs
1447061 -- 40 um xtals
1447062 -- 25 um xtals
1447063 -- 10 um xtals
1447064 -- 5 um xtals
1447073 -- 2 um xtals

walltime ranged from 19 to 46 minutes for one job on 64 nodes (1024 tasks) for 131k images

##### analysing results for cytochrome:
```
export cyto_pdb=$MODULES/exafel_project/kpp-frontier/cytochrome/5wp2.pdb
`
JOB_ID_STAGE2=1447061; JOB_ID_MERGE=1427767; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/cytochrome/$JOB_ID_MERGE/out/ly99sim_all.mtz stage2=$SCRATCH/reservation02/$JOB_ID_STAGE2/$JOB_ID_STAGE2 pdb=$cyto_pdb n_bins=10 stat=cc_anom
JOB_ID_STAGE2=1447062; JOB_ID_MERGE=1429661; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/cytochrome/$JOB_ID_MERGE/out/ly99sim_all.mtz stage2=$SCRATCH/reservation02/$JOB_ID_STAGE2/$JOB_ID_STAGE2 pdb=$cyto_pdb n_bins=10 stat=cc_anom
JOB_ID_STAGE2=1447063; JOB_ID_MERGE=1427786; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/cytochrome/$JOB_ID_MERGE/out/ly99sim_all.mtz stage2=$SCRATCH/reservation02/$JOB_ID_STAGE2/$JOB_ID_STAGE2 pdb=$cyto_pdb n_bins=10 stat=cc_anom
JOB_ID_STAGE2=1447064; JOB_ID_MERGE=1427787; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/cytochrome/$JOB_ID_MERGE/out/ly99sim_all.mtz stage2=$SCRATCH/reservation02/$JOB_ID_STAGE2/$JOB_ID_STAGE2 pdb=$cyto_pdb n_bins=10 stat=cc_anom
JOB_ID_STAGE2=1447073; JOB_ID_MERGE=1429662; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/cytochrome/$JOB_ID_MERGE/out/ly99sim_all.mtz stage2=$SCRATCH/reservation02/$JOB_ID_STAGE2/$JOB_ID_STAGE2 pdb=$cyto_pdb n_bins=10 stat=cc_anom
```
plots are saved to /lustre/orion/chm137/proj-shared/cctbx/reservation02/eval_plots

#### lysozyme runs
1447065 -- 2 um xtals
1447066 -- 1 um xtals
1447067 -- 0.5 um xtals
1447068 -- 0.25 um xtals
1447070 -- 0.125 um xtals

walltime ranged from 24 to 29 minutes for one job on 64 nodes (1024 tasks) for 131k images

##### analyzing results for lysozyme:
```
export lyso_pdb=$MODULES/exafel_project/kpp-frontier/yb_lyso/4bs7.pdb

JOB_ID_STAGE2=1447065; JOB_ID_MERGE=1427835; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/yb_lyso/$JOB_ID_MERGE/out/yb_lyso_500k_all.mtz stage2=$SCRATCH/reservation02/$JOB_ID_STAGE2/$JOB_ID_STAGE2 pdb=$lyso_pdb n_bins=10 stat=cc_anom
JOB_ID_STAGE2=1447066; JOB_ID_MERGE=1427900; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/yb_lyso/$JOB_ID_MERGE/out/yb_lyso_500k_all.mtz stage2=$SCRATCH/reservation02/$JOB_ID_STAGE2/$JOB_ID_STAGE2 pdb=$lyso_pdb n_bins=10 stat=cc_anom
JOB_ID_STAGE2=1447067; JOB_ID_MERGE=1427901; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/yb_lyso/$JOB_ID_MERGE/out/yb_lyso_500k_all.mtz stage2=$SCRATCH/reservation02/$JOB_ID_STAGE2/$JOB_ID_STAGE2 pdb=$lyso_pdb n_bins=10 stat=cc_anom
JOB_ID_STAGE2=1447068; JOB_ID_MERGE=1427902; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/yb_lyso/$JOB_ID_MERGE/out/yb_lyso_500k_all.mtz stage2=$SCRATCH/reservation02/$JOB_ID_STAGE2/$JOB_ID_STAGE2 pdb=$lyso_pdb n_bins=10 stat=cc_anom
JOB_ID_STAGE2=1447070; JOB_ID_MERGE=1427903; libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py mtz=$SCRATCH/yb_lyso/$JOB_ID_MERGE/out/yb_lyso_500k_all.mtz stage2=$SCRATCH/reservation02/$JOB_ID_STAGE2/$JOB_ID_STAGE2 pdb=$lyso_pdb n_bins=10 stat=cc_anom

```
plots are saved to /lustre/orion/chm137/proj-shared/cctbx/reservation02/eval_plots

### using the extra time on the reservation

#### two jobs on 256 nodes each

Thermolysin, job 1447100, completed successfully on 256 nodes (4096 tasks) in 32 minutes.

Cry11Ba was submitted three times, as jobs 1447099, 1447112, and 1447128. The first two failed with different MPI errors relatively early on. The third timed out late in the reservation. The timeout is not a great surprise but the persistent MPI errors suggest we may need to ease up further on the number of tasks.

#### testing multiple srun jobs in one batch job

Smaller blocks of available nodes were used to run 80-node batch jobs containing five srun commands on 16 nodes each. These are documented in kpp-frontier/no_reservation and output is in $SCRATCH/no_reservation.

For a smaller test, jobs 1447157 and 1447159 processed only 3000 images of lysozyme and cytochrome, respectively, on five different crystal sizes simultaneously. In both cases all srun jobs started simultaneously and finished at similar times. Logging, output, etc. are properly demangled.

Taking the above as a success, the test was expanded to 30k shots. The lysozyme job was able to start and finish within the reservaiton time (1447183). All five srun jobs completed in under 42 minutes each, and the batch job itself took just over 42 minutes (<1 minute overhead). A cytochrome job was submitted to the queue but did not run in time.
