# ExaFEL evaluation

## Introduction

Directly citing the ExaFEL KPP-2 Writeup received from Nick, the quality
of results is to be evaluated using the following five figures of merit:

1) **A** – Geometrical fit between model and experiment;
2) **B** – Internal self-consistency of the intensity profile;
3) **C** – Precision of modeling the Bragg spot intensities;
4) **D** – Physical accuracy of the measurements;
5) **E** – Accuracy of the anomalous signal.

Individual figures of merit can be calculated using the `step_$#.sh` shell
files accessible in this directory. The steps are organised using letters
`$` from A–E to mark individual metrics and numbers `#` for subsequent steps.
Each of these figures of merit is described further in the KPP write-up,
as well as in the [Google Docs file][link], accessible upon request.

[link]: https://docs.google.com/document/d/1XASZ3kjKgaWATuBiOGzjiwQWW8jlw6K4hY0wTtSOnNA





## Requirements

Running all ExaFEL evaluation scripts presented in this directory
requires a cctbx installation with the following modules and branches:

- `cctbx_project` – any recent branch
- `dials` – any recent branch (`dsp_oldstriping` suggested for processing)
- `exafel_project` – this branch (the instructions may differ between branches)
- `LS49` – any recent branch
- `ls49_big_data` – any recent branch
- `psii_spread` – any recent branch

Additionally, the following git diff must be applied to the `cctbx_project`
module, independent on the branch used. The cpp part is mostly irrelevant,
so the cctbx does not need to be rebuilt after introducing the patch.

    diff --git a/simtbx/diffBragg/src/diffBragg.cpp b/simtbx/diffBragg/src/diffBragg.cpp
    index c7b1e08bc3..a893b423c7 100644
    --- a/simtbx/diffBragg/src/diffBragg.cpp
    +++ b/simtbx/diffBragg/src/diffBragg.cpp
    @@ -1817,6 +1817,7 @@ void diffBragg::add_diffBragg_spots(const af::shared<size_t>& panels_fasts_slows

         Npix_to_model = panels_fasts_slows.size()/3;
        SCITBX_ASSERT(Npix_to_model <= Npix_total);
        +    raw_pixels_roi = af::flex_double(Npix_to_model); // NKS, only way to correctly size & zero array
         double * floatimage_roi = raw_pixels_roi.begin();

         diffBragg_rot_mats();
    diff --git a/xfel/merging/command_line/merge.py b/xfel/merging/command_line/merge.py
    index f045308541..0591ff200b 100644
    --- a/xfel/merging/command_line/merge.py
    +++ b/xfel/merging/command_line/merge.py
    @@ -45,6 +45,7 @@ class Script(object):
       def __init__(self):
         self.mpi_helper = mpi_helper()
         self.mpi_logger = mpi_logger()
    +    self.common_store = dict(foo="hello") # always volatile, no serialization, no particular dict keys guaranteed

       def __del__(self):
         self.mpi_helper.finalize()
    @@ -165,6 +166,7 @@ class Script(object):
         # Perform phil validation up front
         for worker in workers:
           worker.validate()
    +      worker.__dict__["common_store"] = self.common_store
         self.mpi_logger.log_step_time("CREATE_WORKERS", True)

         # Do the work






## Tools
### Analysing offsets using diffBragg benchmark
*Associated goals*: **A**; *files:*
[evaluate_prediction_offset.py](evaluate_prediction_offset.py)

In order to evaluate the difference between reflection position offsets
calculated by diffBragg versus DIALS, the expanded diffBragg benchmark script
[evaluate_prediction_offset.py](evaluate_prediction_offset.py) can be used.
This code was originally introduced by Derek Mendez and further adapted
by Daniel Tchoń. It uses the information stored in .refl files after stage 1
to calculate radial, transverse, and overall offset across resolution bins.

```shell
libtbx.python $MODULES/exafel_project/kpp_eval/evaluate_prediction_offset.py \
stage1=$SCRATCH/yb_lyso/13296752/stage1 d_min=2.0
```

By default, all data stored in `stage1/refls` between `d_min` and `d_max`
will be grouped into `n_bins` and `stat=median` for each bin as well as
the entire range will be reported. Calculated statistic can be also set
to `average` (arithmetic mean) or `rms` (matches the annulus approach).
While ill-advised, `bins` can be made `same_count` to reflect the original
behavior of the script. Usually, only `stage1` and `d_min` will be set.

### Analysing offsets using annulus worker
*Associated goals*: **A**; *files:*
[step_A1.sh](step_A1.sh), [step_A1.sh](step_A1.sh), 
[step_A1.sh](step_A3.sh), [step_A1.sh](step_A4.sh),
[fixup_hopper_identifiers.py](fixup_hopper_identifiers.py).

Other than using the dedicated script, offset rms can be also calculated
using the annulus worker deliverables code. This should be considered a backup
method. It can be achieved by copying and filling the environment variables
in shell scripts `step_A#.sh`, where # can be 1, 2, 3 or 4.
Steps 1 and 2 run the annulus worker on the common set of indexed DIALS (1)
and diffBragg (2) reflections. They collect information from the offset columns
to produce an average offset vs resolution table as a part of the main output.

```shell
cp $MODULES/exafel_project/kpp_eval/step_A1.sh .
vi step_A1.sh  # to fill the environment variables
sbatch step_A1.sh
```

Step 2 can be processed in the same way. If there are any problems mismatch
between stage 2 expt and refl identifiers, these can be most likely fixed
by appropriately fixing the files with `fixup_hopper_identifiers.py`.
Mind this analysis can be performed
on just a small subset of data, e.g. 3000 experiments.
In order to further analyse individual detector panels,
one can `cp`, edit and `source` steps 3 and 4 in a similar fashion.

### Evaluating cross-correlation of odd and even intensities
*Associated goals*: **C**; *files:*
[evaluate_cc12.py](evaluate_cc12.py),
[step_C.sh](step_C.sh).

Precision of intensities modeling has been proposed to utilise a difference
between "odd" and "even" half-sets of intensities refined by diffBragg.
Since stage 2 can produce an `.mtz` file, this can be easily done by calling
stage 2 refinement of half-datasets followed by a script that calculates
a cross-correlation coefficient between two such files,
called here `evaluate_cc12.py`. The python script can be called directly,
by providing mtz paths as arguments, or by calling a modified shell script:
```shell
cp $MODULES/exafel_project/kpp_eval/step_C.sh .
vi step_C.sh  # to fill mtz paths
source step_C.sh
```

### Calculating ground-truth R-factor and strength of anomalous signal
*Associated goals*: **D**, **E**;
*files:*
[evaluate_stage2_convergence.py](evaluate_stage2_convergence.py),
[evaluate_anom.py](evaluate_anom.py),
[step_DE.sh](step_DE.sh).

R-factor and anomalous signal strength can be automatically calculated
by loading reference `.pdb` and refined `.mtz` files using existing
`mmtbx.command_line.load_model_and_data`. The import step will automatically
print the "R_work" value, which in this case can be better described as "R_gt".
Anomalous map summary and peak heights for selected atoms will be then printed
for selected atoms using modified `xfel.peak_height_at_atom` call.

```shell
cp $MODULES/exafel_project/kpp_eval/step_DE.sh .
vi step_DE.sh  # to fill pdb, mtz paths and anomalous element selection.
source step_DE.sh
```

In the case of pdb code 4bs7 (Ytterbium lysozyme), the results can be made
slightly more precise by importing exactly the same anomalous dispersion
parameters as the ones used to simulate the images. This can be done by
calling the dedicated `evaluate_anom_4bs7.py` script instead.

### Tracing the evolution of agreement parameters
*Associated goals*: **C**, **D**, **E**;
*files:*
[evaluate_stage2_convergence.py](evaluate_stage2_convergence.py).

Other than investigating the last step or output of diffBragg only,
the progress of stage 2 can be traced as a function of iteration step
using `evaluate_stage2_convergence.py`. This heavily modified version
of previous Vidya's script can plot many aforementioned and other statistics,
as well as scatter refined vs reference data based on diffBragg `.npz` files.
It can be called directly with either a large set of phil parameters
(see example below and help message for full documentation) or by defining
appropriate environmental variables (see [README.md](../kpp-docs/README.md)).

`libtbx.ipython $MODULES/exafel_project/kpp_eval/evaluate_stage2_convergence.py
mtz=/path/to/dials/merged.mtz stage2=/path/to/stage2/directory/
pdb=/path/to/reference.pdb n_bins=10 d_min=1.9
stat=cc_anom scatter_ranges='-1:2,100:500:100,450' show=True`

The script was initially not intended to be used as a stand-alone evaluation
tool, but it might prove useful as one, as it allows to calculate
statistics that are not yielded by other code, for example CC coefficient
between anomalous signals of the Friedel pairs.


## Results

### **A** – Geometrical fit between model and experiment
The overall offset RMS is smaller after DIALS compared to the stage 1.
DiffBragg gives tighter distribution at low-resolution, but due to the presence
of divereged outliers, the RMS is significantly larger at high resolutions.
This remains true even after the mosaic outliers have been preserved.
The following tables come from the offset analysis:

**DIALS spotfinding, no outliers**:

```text
 Resolution range N possible refl_cnt  rmsd  rms_radial_offset rms_tangential_offset Correl ΔR,ΔΨ Correl ΔT,ΔΨ
-1.0000 -  3.8780    1688     300842  0.30px       0.27px              0.13px           -55.0%       -1.7%
 3.8780 -  3.0780    1641     168506  0.43px       0.40px              0.16px           -76.3%       -7.6%
 3.0780 -  2.6888    1634     125596  0.48px       0.44px              0.18px           -72.5%       -7.2%
 2.6888 -  2.4430    1620      98771  0.50px       0.45px              0.20px           -68.3%       -4.8%
 2.4430 -  2.2679    1643      82334  0.51px       0.46px              0.22px           -64.5%       -3.4%
 2.2679 -  2.1341    1617      61082  0.51px       0.45px              0.24px           -59.5%        1.5%
 2.1341 -  2.0272    1630      51394  0.51px       0.45px              0.25px           -56.3%        4.9%
 2.0272 -  1.9390    1623      43328  0.51px       0.44px              0.26px           -52.6%        5.9%
 1.9390 -  1.8643    1603      10770  0.51px       0.43px              0.26px           -49.5%        8.2%
 1.8643 -  1.8000    1639          0     NaN          NaN                 NaN              NaN         NaN

-1.0000 -  1.8000   16338     942623  0.43px       0.39px              0.18px           -53.2%       -2.3%
```

**Stage1 hopper, no outliers**:

```text
 Resolution range N possible refl_cnt  rmsd  rms_radial_offset rms_tangential_offset Correl ΔR,ΔΨ Correl ΔT,ΔΨ
-1.0000 -  3.8780    1688     300842  0.21px       0.17px              0.12px            9.3%         -2.6%
 3.8780 -  3.0780    1641     168506  0.47px       0.44px              0.18px           57.6%        -10.4%
 3.0780 -  2.6888    1634     125596  0.81px       0.78px              0.20px           71.2%        -11.9%
 2.6888 -  2.4430    1620      98771  1.09px       1.07px              0.23px           76.5%        -10.4%
 2.4430 -  2.2679    1643      82333  1.27px       1.25px              0.25px           78.6%         -8.9%
 2.2679 -  2.1341    1617      61082  1.36px       1.33px              0.26px           78.6%         -3.1%
 2.1341 -  2.0272    1630      51393  1.41px       1.38px              0.28px           79.4%          0.8%
 2.0272 -  1.9390    1623      43328  1.43px       1.40px              0.29px           79.1%          2.2%
 1.9390 -  1.8643    1603      10770  1.43px       1.40px              0.29px           78.5%          5.4%
 1.8643 -  1.8000    1639          0     NaN          NaN                 NaN             NaN           NaN

-1.0000 -  1.8000   16338     942621  0.87px       0.84px              0.20px           37.4%        -4.7%
```

If we were to actively reject outliers, diffBragg reflection positions
match the experiment better. This can be observed by investigating median
of distribution instead of RMS. The following tables, generated using 
[evaluate_prediction_offset.py](evaluate_prediction_offset.py) show,
that stage 1 outperforms DIALS if we exclude outliers from the analysis.
The following table was made using another, yet roughly equivalent dataset:

```text
               DIALS_offset  DIALS_rad  DIALS_tang  dB_offset    dB_rad   dB_tang  resolution
bin                                                                                          
9999.0-4.3088      0.247351   0.152383    0.120455   0.118860  0.072417  0.061575    6.062287
4.3088-3.4199      0.284406   0.200665    0.124694   0.198407  0.139666  0.091892    3.832891
3.4199-2.9876      0.301684   0.212777    0.134396   0.261555  0.197081  0.110027    3.205908
2.9876-2.7144      0.311426   0.215461    0.145152   0.299245  0.223339  0.124630    2.862027
2.7144-2.5198      0.331634   0.226399    0.160510   0.327941  0.237944  0.141626    2.645762
2.5198-2.3712      0.346003   0.230592    0.170970   0.362277  0.251113  0.170580    2.471097
2.3712-2.2524      0.330443   0.211573    0.172685   0.371709  0.245431  0.175785    2.347139
2.2524-2.1544      0.330210   0.204265    0.171586   0.380250  0.236399  0.175685    2.228373
2.1544-2.0714      0.408785   0.386731    0.132046   0.303067  0.200925  0.221527    2.147640
2.0714-2.0000           NaN        NaN         NaN        NaN       NaN       NaN         NaN
9999.0-2.0000      0.269951   0.176113    0.125548   0.161654  0.104286  0.077835    4.429696
```



### **C** – The precision of modeling intensities

The script for calculating cc1/2 between two half-sets of data refined
by diffBragg is ready and available. It hasn't been used to test the agreement
of the half-sets yet, but it was used to test the agreement between 
DIALS and stage2 refinements. The results show good agreement
at medium-resolution range and decent agreement in low- and high-resolution.
This agrees with conclusions from other tests performed here.

```text
    d_max     d_min  #obs_asu / #thr_asu    cc1/2
--------------------------------------------------
( -1.0000,   4.3082)     1575 /     1580  82.2677%
(  4.3082,   3.4194)     1575 /     1575  94.5610%
(  3.4194,   2.9871)     1585 /     1585  92.9034%
(  2.9871,   2.7140)     1570 /     1570  94.7748%
(  2.7140,   2.5194)     1569 /     1569  94.6731%
(  2.5194,   2.3709)     1575 /     1575  92.8068%
(  2.3709,   2.2521)     1566 /     1566  91.7605%
(  2.2521,   2.1541)     1571 /     1571  82.6398%
(  2.1541,   2.0711)     1596 /     1598  66.5851%
(  2.0711,   1.9997)     1039 /     1555  68.3675%
--------------------------------------------------
( -1.0000,   1.9997)    15221 /    15744  73.3101%
```


### **D & E** – Accuracy of measurement and anomalous signal
Based on the results of Vidya's ExaFEL pipeline for 20k frames,
the diffBragg-refined mtz fits the reference pdb marginally better than DIALS.
The values of R-work for DIALS and stage2 are 0.0675 and 0.0631, respectively.
However, the anomalous signal peak height at iron positions are marginally
lower (maximum 20.99σ vs 20.60σ). 

Subsequent tests performed using files generated by Derek's pipeline,
which apparently converges much faster, show that diffBragg improves R1 fit,
but does not really affect anomalous signal. The decrease of R-work from 0.1145
to 0.0723 results more likely from fitting mostly to low-resolution i.e. more
intense i.e. higher-weighted spots.

**DIALS merge, 1800 images from Derek's pipeline provided by Nick**

```text
                  ----------F(model) initialization----------

Twinning will be detected automatically.
                   start: r(all,work,free)=0.1370 0.1370 0.1370 n_refl.: 15209
       re-set all scales: r(all,work,free)=0.1370 0.1370 0.1370 n_refl.: 15209
         remove outliers: r(all,work,free)=0.1370 0.1370 0.1370 n_refl.: 15209
bulk-solvent and scaling: r(all,work,free)=0.1145 0.1145 0.1145 n_refl.: 15209
         remove outliers: r(all,work,free)=0.1145 0.1145 0.1145 n_refl.: 15209
|--(resolution: 2.00 - 27.96 A, n_refl.=15209 (all), 100.00% free)------------|
|                                                                             |
| r_work= 0.1145 r_free= 0.1145 coordinate error (max.-lik. estimate): 0.17 A |
|                                                                             |
| normalized target function (ml) (work): 4.561293                            |
| target function (ml) not normalized (work): 69372.701814                    |
| target function (ml) not normalized (free):            None                 |
|-----------------------------------------------------------------------------|

End of input processing

                        ----------Map analysis----------

Grid points 5-number summary:
minimum:               -4.69σ
quartile1:             -0.66σ
median:                -0.01σ
quartile3:              0.65σ
maximum:               17.26σ

pdb=" SG  CYS A   6 ":   0.78σ
pdb=" SD  MET A  12 ":  -0.25σ
pdb=" SG  CYS A  30 ":   0.36σ
pdb=" SG  CYS A  64 ":   0.77σ
pdb=" SG  CYS A  76 ":   0.93σ
pdb=" SG  CYS A  80 ":   2.15σ
pdb=" SG  CYS A  94 ":   0.85σ
pdb=" SD  MET A 105 ":   1.64σ
pdb=" SG  CYS A 115 ":   0.78σ
pdb=" SG  CYS A 127 ":   1.95σ
```


**stage2 merge, 1800 images from Derek's pipeline provided by Nick**

```text
                  ----------F(model) initialization----------

Twinning will be detected automatically.
                   start: r(all,work,free)=0.0745 0.0745 0.0745 n_refl.: 15221
       re-set all scales: r(all,work,free)=0.0745 0.0745 0.0745 n_refl.: 15221
         remove outliers: r(all,work,free)=0.0744 0.0744 0.0744 n_refl.: 15220
bulk-solvent and scaling: r(all,work,free)=0.0723 0.0723 0.0723 n_refl.: 15220
         remove outliers: r(all,work,free)=0.0723 0.0723 0.0723 n_refl.: 15220
|--(resolution: 2.00 - 27.97 A, n_refl.=15220 (all), 100.00% free)------------|
|                                                                             |
| r_work= 0.0723 r_free= 0.0723 coordinate error (max.-lik. estimate): 0.17 A |
|                                                                             |
| normalized target function (ml) (work): 3.988605                            |
| target function (ml) not normalized (work): 60706.575691                    |
| target function (ml) not normalized (free):            None                 |
|-----------------------------------------------------------------------------|

End of input processing

                        ----------Map analysis----------

Grid points 5-number summary:
minimum:               -4.30σ
quartile1:             -0.66σ
median:                -0.01σ
quartile3:              0.65σ
maximum:               20.67σ

pdb=" SG  CYS A   6 ":   1.95σ
pdb=" SD  MET A  12 ":   0.88σ
pdb=" SG  CYS A  30 ":  -1.96σ
pdb=" SG  CYS A  64 ":   1.18σ
pdb=" SG  CYS A  76 ":   0.84σ
pdb=" SG  CYS A  80 ":   1.82σ
pdb=" SG  CYS A  94 ":   2.52σ
pdb=" SD  MET A 105 ":   1.97σ
pdb=" SG  CYS A 115 ":   1.27σ
pdb=" SG  CYS A 127 ":   0.82σ
```

### Summary

Based on the evidence provided by Vidya's and Derek's pipelines,
diffBragg models low-resolution much better due to its higher intensity,
which improves R-work, improves offset on low resolution but worsens it
at high resolution, and does not significantly affect the anomalous signal.
However, these are only based on preliminary evaluations – evaluations
performed on 130k and 500k image datasets in August have already shown,
that the convergence of statistics such as R-factor and CC_anom can differ
quite significantly between individual cases, as discussed in the google space.

