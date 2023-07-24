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

### **D & E** – Accuracy of measurement and anomalous signal
Based on the results of Vidya's ExaFEL pipeline for 20k frames,
the diffBragg-refined mtz fits the reference pdb marginally better than DIALS.
The values of Rwork for DIALS and stage2 are 0.0675 and 0.0631, respectively.
However, the anomalous signal peak height at iron positions are marginally
lower (maximum 20.99σ vs 20.60σ). Based on these evidence it is ambiguous
which dataset represents the reference structure better.

**DIALS merge**

                      ----------F(model) initialization----------                  
    
    Twinning will be detected automatically.
                       start: r(all,work,free)=0.1833 0.1833 0.1833 n_refl.: 27250
           re-set all scales: r(all,work,free)=0.1833 0.1833 0.1833 n_refl.: 27250
             remove outliers: r(all,work,free)=0.1828 0.1828 0.1828 n_refl.: 27239
    bulk-solvent and scaling: r(all,work,free)=0.0675 0.0675 0.0675 n_refl.: 27239
             remove outliers: r(all,work,free)=0.0675 0.0675 0.0675 n_refl.: 27239
    |--(resolution: 1.90 - 44.29 A, n_refl.=27239 (all), 100.00% free)------------|
    |                                                                             |
    | r_work= 0.0675 r_free= 0.0675 coordinate error (max.-lik. estimate): 0.09 A |
    |                                                                             |
    | normalized target function (ml) (work): 4.520227                            |
    | target function (ml) not normalized (work): 123126.465831                   |
    | target function (ml) not normalized (free):            None                 |
    |-----------------------------------------------------------------------------|
    
    End of input processing
    
                            ----------Map analysis----------                       
    
    Grid points 5-number summary:
    minimum:               -4.45σ
    quartile1:             -0.66σ
    median:                -0.00σ
    quartile3:              0.65σ
    maximum:               20.99σ
    
    pdb="FE1  FES A 201 ":  20.25σ
    pdb="FE2  FES A 201 ":  21.17σ
    pdb="FE1  FES B 202 ":  21.24σ
    pdb="FE2  FES B 202 ":  20.57σ


**stage2 merge, Vidya's pipeline**

                  ----------F(model) initialization----------                  

    Twinning will be detected automatically.
                       start: r(all,work,free)=0.1822 0.1822 0.1822 n_refl.: 27250
           re-set all scales: r(all,work,free)=0.1822 0.1822 0.1822 n_refl.: 27250
             remove outliers: r(all,work,free)=0.1825 0.1825 0.1825 n_refl.: 27231
    bulk-solvent and scaling: r(all,work,free)=0.0631 0.0631 0.0631 n_refl.: 27231
             remove outliers: r(all,work,free)=0.0631 0.0631 0.0631 n_refl.: 27231
    |--(resolution: 1.90 - 44.27 A, n_refl.=27231 (all), 100.00% free)------------|
    |                                                                             |
    | r_work= 0.0631 r_free= 0.0631 coordinate error (max.-lik. estimate): 0.09 A |
    |                                                                             |
    | normalized target function (ml) (work): 4.441006                            |
    | target function (ml) not normalized (work): 120933.046333                   |
    | target function (ml) not normalized (free):            None                 |
    |-----------------------------------------------------------------------------|
    
    End of input processing
    
                            ----------Map analysis----------                       
    
    Grid points 5-number summary:
    minimum:               -4.35σ
    quartile1:             -0.66σ
    median:                -0.00σ
    quartile3:              0.65σ
    maximum:               20.60σ
    
    pdb="FE1  FES A 201 ":  19.91σ
    pdb="FE2  FES A 201 ":  20.84σ
    pdb="FE1  FES B 202 ":  20.83σ
    pdb="FE2  FES B 202 ":  20.38σ

TODO: test Derek's pipeline, which apparently converges much faster.


