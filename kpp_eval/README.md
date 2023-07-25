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
- `dials` – any recent branch
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

## Results

### **A** – Geometrical fit between model and experiment
Currently, the overall offset RMSD appers to be better (smaller)
after DIALS compared to the diffBragg stage 1. DiffBragg appears to
give slightly tighter distribution for low-resolution, but significantly
larger scatter at high resolutions. Unless some part of indexing is not
performed or analyzed correctly, this remains true even
after the mosaic outliers have been preserved:

**DIALS spotfinding, no outliers**:

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


**Stage1 hopper, no outliers**:

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


### **C** – The precision of modeling intensities

The script for calculating cc1/2 between two half-sets of data refined
by diffBragg is ready and available. It hasn't been used to test the agreement
of the half-sets yet, but it was used to test the agreement between 
DIALS and stage2 refinements. The results show good agreement
at medium-resolution range and decent agreement in low- and high-resolution.
This agrees with conclusions from other tests performed here.

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


**stage2 merge, 1800 images from Derek's pipeline provided by Nick**

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

### Summary

Based on the evidence provided by Vidya's and Derek's pipelines,
diffBragg models low-resolution much better due to its higher intensity,
which improves R-work, improves offset on low resolution but worsens it
at high resolution, and does not significantly affect the anomalous signal.
