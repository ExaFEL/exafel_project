from datetime import datetime
from libtbx.mpi4py import MPI


def bcast_dict_1by1(comm, data, root=0):
  """Broadcast dictionary elements one-by-one to avoid MPI overflow issues"""
  rank = comm.rank
  print(f'bcast1: {comm.rank=}, {datetime.now()=}')
  received = {}
  keys = list(data.keys()) if data is not None else None
  keys = comm.bcast(keys, root=root)
  for key in keys:
    print(f'bcast2: {key=}, {datetime.now()=}')
    value = data[key] if rank == root else None
    received[key] = comm.bcast(value, root=root)
  print(f'bcast3: {comm.rank=}, {datetime.now()=}')
  return received


def collect_dict_1by1(comm, data, root=0):
  """Gather dictionary elements by sending them one-by-one to avoid overflow"""
  rank = comm.rank
  print(f'gather1: {rank=}, {len(data)=}, {datetime.now()=}')
  received = []
  max_data_length = comm.reduce(len(data), op=MPI.MAX, root=root)
  max_data_length = comm.bcast(max_data_length, root=root)
  data_list = list(data.items()) + [None] * max_data_length
  for data_row in range(max_data_length):
    print(f'gather2: {data_row=}, {datetime.now()=}')
    gathered = comm.gather(data_list[data_row], root=root)
    if rank == root:
      received.extend(g for g in gathered if g is not None)
  print(f'gather3: {rank=}, {len(received)=}, {datetime.now()=}')
  return {r[0]: r[1] for r in received if r is not None} \
    if rank == root else None
