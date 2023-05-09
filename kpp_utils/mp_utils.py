from datetime import datetime
from libtbx.mpi4py import MPI


def bcast_dict_1by1(comm, data, root=0):
  """Broadcast dictionary elements one-by-one to avoid MPI overflow issues"""
  print(f'bcast1: {comm.rank=}, {datetime.now()=}')
  received = {}
  keys = comm.bcast(list(data.keys()), root=root)
  for key in keys:
    print(f'bcast2: {key=}, {datetime.now()=}')
    received[key] = comm.bcast(data[key], root=root)
  print(f'bcast3: {comm.rank=}, {datetime.now()=}')
  return received


def gather_dict_1by1(comm, data, root=0):
  """Gather dictionary elements by sending them one-by-one to avoid overflow"""
  rank = comm.rank
  print(f'gather1: {rank=}, {datetime.now()=}')
  received = {}
  key_rank_map = {key: rank for key in data.keys()}
  if rank == 0:
    key_rank_list = comm.gather(key_rank_map, root=root)
    for key_rank_from_single_rank in key_rank_list:
      key_rank_map.update(key_rank_from_single_rank)
  key_rank_map = comm.bcast(key_rank_map, root=root)
  for key, source in key_rank_map.items():
    print(f'gather2: {key=}, {datetime.now()=}')
    received[key] = comm.sendrecv(data[key], dest=root, source=source)
  print(f'gather3: {rank=}, {datetime.now()=}')
  return received


def gather_dict_1by1_alt(comm, data, root=0):
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
  return received if rank == root else None
