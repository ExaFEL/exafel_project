This adds the ability to simulate images with model structure factors based on experimental Fobs
rather than just Fcalc.  In addition, the Fobs can be downloaded on-the-fly using a PDB code, or
alternatively read from a local file. The matrix of possible data input is therefore: 

| crystal.pdb.coefficients  | crystal.pdb.source=code | crystal.pdb.source=file |
|---------------------------|-------------------------|-------------------------|
| =fcalc                    |                         |                         |
| =fobs                     |                         |                         |

Here is example phil input specifying Fobs structure factors downloaded from the PDB:
```
crystal {
  structure=pdb
  pdb {
    source=code
    code=4tnl
    coefficients=fobs
    label=pdbx_I
  }
  length_um=5.
}
```
Note that in this instance, the CIF reader will search for a data item whose label contains
the string "pdbx_I", using that data for the structure factors.  Column data is automatically 
cast to intensities (observed amplitudes would be squared).
