# Interactive and batched diffBragg trial job submission

The interactive scripts contained in this directory allow for quick, reproducible execution of the diffBragg workflow steps in interactive SLURM jobs. Jobs are presumed to be executed in the expected sequence with the same set of arguments to diffBragg; i.e., the user should make one selection of each of the following variables:

1. sample: which molecule to simulate as the contents of the crystal (cytochrome, yb_lyso, thermolysin or cry11ba)
2. n_thousand: number of thousands (actually multiples of 1024) of crystals to simulate to compose a dataset
3. length: simulated crystal length in microns
4. detdist: simulated sample-to-detector distance in millimeters
5. dmin: high resolution limit for simulated data and analysis
6. tag: any meaningful identifier to use to label the output

and ensure the output of a completed previous step is present for the same variables before running a later step, in this order:

1. interactive_sim: simulation of diffraction images
2. interactive_index: conventional processing of XFEL diffraction images with cctbx.xfel
3. interactive_merge: conventional processing of indexed and integrated images with cctbx.xfel.merge
4. interactive_split: preparation of the merging results for ingestion into diffBragg
5. interactive_stage1: local refinement of the crystal models against individual images
6. interactive_predict: generation of new predicted pixel intensities at every measured reflection based on the refined models from stage1
7. interactive_stage2: global refinement of structure factors to optimize the agreement of the newly predicted pixel intensities and the observed ones

A script `batch.sh` is also provided for executing all these steps in sequence. A reference for which steps require which arguments can be found in this script. Note that the output directory from the previous step is always one of the arguments to the following step.

## Parameterization

For each of the samples prepared as part of the ExaFEL KPPs for diffBragg, the following are the current recommended parameter sets. Note also that the sample name must exactly match one of `cytochrome`, `yb_lyso`, `thermolysin` or `cry11ba`. On the other hand, the value of `tag` is purely at the discretion of the user, and n_thousand depends on the desired scale (typically from 65 up to 500).

| sample      | length (um) | detdist | dmin |
|-------------|-------------|---------|------|
| cytochrome  | 2-40        | 30      | 1.5  |
| yb_lyso     | 0.125-2     | 80      | 1.9  |
| thermolysin | 0.5-20      | 80      | 1.9  |
| cry11ba     | 0.5-16      | 160     | 2.4  |


