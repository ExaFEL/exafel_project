# Table of Results for Thermolysin Processing of 130,000 Images

| step                       | walltime | nodes | ranks | node type | inodes | disk space | JOB ID   |
| -------------------------- | -------- | ----- | ----- | --------- | ------ | ---------- |----------|
| Image creation             | 59:51    | 64    | 2048  | gpu       | 6146   | 2.3T       | 13719137 |
| DIALS indexing/integration | 53:37    | 8     | 256   | cpu       | 3072   | 431G       | 14199866 |
| DIALS merging              | 11:12    | 16    | 512   | cpu       | 2565   | 4.3G       | 14297594 |
| diffBragg hopper           | 48:08    | 64    | 1024  | gpu       | 1027   | 105M       | 14310798 |
| diffBragg integrate        | 45:59    | 64    | 1024  | gpu       | 2053   | 123G       | 14314404 |
| diffBragg stage 2          | 39:32    | 256   | 4096  | gpu       | 1419   | 19G        | 14349584 |



Output of `evaluate_stage2_convergence.py` in `/global/cfs/cdirs/m3562/users/vidyagan/p20231/thermolysin`.