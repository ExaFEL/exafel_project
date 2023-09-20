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


For lysozyme:
```
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/yb_lyso_131k_stage2.sh 1411658 1411870 1415195
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/yb_lyso_131k_stage2.sh 1427014 1427835 1428320
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/yb_lyso_131k_stage2.sh 1427017 1427900 1428322
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/yb_lyso_131k_stage2.sh 1411658 1427901 1428333
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/yb_lyso_131k_stage2.sh 1427020 1427902 1428365
```

For cytochrome:
```
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cytochrome_131k_stage2.sh 1426077 1427767 1435064
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cytochrome_131k_stage2.sh 1429648 1429661 1434948
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cytochrome_131k_stage2.sh 1427782 1427786 1435065
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cytochrome_131k_stage2.sh 1427783 1427787 1435069
sbatch --reservation=$RESERVATION_NAME $MODULES/exafel_project/kpp-frontier/reservation02/cytochrome_131k_stage2.sh 1429649 1429662 1435711
```
