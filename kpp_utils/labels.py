from __future__ import division
from iotbx import reflection_file_reader
def run(code_or_file):
  direct_algo_res_limit = 1.85

  if len(code_or_file)==4: # for the moment codes are always 4 characters
    from iotbx.pdb.fetch import fetch
    lines = fetch(id=code_or_file,data_type="xray",format="cif")
    miller_arrays = reflection_file_reader.cif_reader(file_object = lines).as_miller_arrays()
  else:

    miller_arrays = reflection_file_reader.any_reflection_file(file_name =
      code_or_file).as_miller_arrays()

  for ma in miller_arrays:
    print(ma.info().label_string())

if __name__ == "__main__":
  import sys
  code_or_file = sys.argv[1]
  run(code_or_file)
