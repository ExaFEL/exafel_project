#sample n_thousand length_microns
BATCH_PATH=$MODULES/exafel_project/post-validate/general/noGT.batch.sh
nshot=24
$BATCH_PATH cyto $nshot 40
$BATCH_PATH yb_lyso $nshot 2
$BATCH_PATH cry11ba $nshot 16
$BATCH_PATH thermo $nshot 20
$BATCH_PATH cry11ba $nshot 0.5
$BATCH_PATH yb_lyso $nshot 0.125
$BATCH_PATH thermo $nshot 1
$BATCH_PATH cyto $nshot 2

