from libtbx.mpi4py import MPI


"""
mpi4py has an internal limit for the length of passed element. The overall size
of sent/received/gathered/broadcasted objects must be smaller than 2**31 bytes.
Attempting to pass a larger object causes an `OverflowError` or `SystemError`.
The dictionaries of structure factors created by the EXAFEL scripts can easily
exceed this internal limit, which can raise errors with ambiguous traceback.
The `*_large_*` functions defined below circumvent this issue by passing values
either one-by-one or in slices, which can negatively affect the execution time
of the preparatory stage, but otherwise circumvents the mpi-related issues.
"""


def bcast_large_dict(comm: MPI.Comm, data: dict, root: int = 0) -> dict:
  """Broadcast dictionary elements one-by-one to avoid MPI overflow issues"""
  on_root = root == comm.rank
  received = {}
  keys = list(data.keys()) if data is not None else None
  keys = comm.bcast(keys, root=root)
  for key in keys:
    value = data[key] if on_root else None
    received[key] = comm.bcast(value, root=root)
  return received


def collect_large_dict(comm: MPI.Comm, data: dict, root: int = 0) -> dict:
  """Gather dictionary elements one-by-one to avoid MPI overflow issues,
  then recreate the dictionary from "gathered" list elements."""
  rank = comm.rank
  on_root = root == rank
  max_data_length = comm.allreduce(len(data), op=MPI.MAX)
  data_list = list(data.items()) + [None] * max_data_length
  received = []
  for i, row in enumerate(range(max_data_length)):
    for j, source in enumerate(range(1, comm.size)):
      tag = i * (comm.size - 1) + j
      comm.barrier()
      if rank == source:
        comm.send(data_list[row], dest=root, tag=tag)
      elif on_root:
        received.append(comm.recv(source=source, tag=tag))
  if on_root:
    data.update({r[0]: r[1] for r in received if r is not None})
  return data if on_root else None
