from sys import getsizeof
from libtbx.mpi4py import MPI


def bcast_large_dict(comm, data, root=0):
  """Broadcast dictionary elements one-by-one to avoid MPI overflow issues"""
  on_root = root == comm.rank
  received = {}
  keys = list(data.keys()) if data is not None else None
  keys = comm.bcast(keys, root=root)
  for key in keys:
    value = data[key] if on_root else None
    received[key] = comm.bcast(value, root=root)
  return received


def collect_large_dict(comm, data, root=0):
  """Gather dictionary elements by sending them one-by-one to avoid overflow"""
  rank = comm.rank
  on_root = root == rank
  max_data_length = comm.reduce(len(data), op=MPI.MAX, root=root)
  max_data_length = comm.bcast(max_data_length, root=root)
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
