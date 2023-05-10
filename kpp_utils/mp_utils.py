from sys import getsizeof
from libtbx.mpi4py import MPI


def bcast_dict(comm, data, root=0):
  """Broadcast dict directly or using one of helper functions if too large"""
  max_data_size = comm.reduce(getsizeof(data), MPI.MAX, root=root)
  max_data_size = comm.bcast(max_data_size, root=root)
  if max_data_size * comm.size < 2 ** 31:
    received = comm.bcast(data, root=root)
  else:
    received = _bcast_dict_1by1(comm=comm, data=data, root=root)
  return received


def _bcast_dict(comm, data, root=0):
  """Broadcast dictionary elements one-by-one to avoid MPI overflow issues"""
  on_root = root == comm.rank
  received = {}
  keys = list(data.keys()) if data is not None else None
  keys = comm.bcast(keys, root=root)
  for key in keys:
    value = data[key] if on_root else None
    received[key] = comm.bcast(value, root=root)
  return received


def collect_dict(comm, data, root=0):
  """Broadcast dict directly or using one of helper functions if too large"""
  max_data_size = comm.reduce(getsizeof(data), MPI.MAX, root=root)
  max_data_size = comm.bcast(max_data_size, root=root)
  max_value_size = max([getsizeof(i) for i in data.values()])
  max_value_size = comm.reduce(max_value_size, MPI.MAX, root=root)
  max_value_size = comm.bcast(max_value_size, root=root)
  if max_data_size * comm.size < 2 ** 31:
    received = {} if comm.rank == root else None
    received_list = comm.gather(data, root=root)
    if comm.rank == root:
      for received_item in received_list:
        received.update(received_item)
  elif max_value_size * comm.size < 2 ** 31:
    received = _bcast_dict_1by1(comm=comm, data=data, root=root)
  else:
    received = _bcast_dict_1by1(comm=comm, data=data, root=root)
  return data


def collect_dict_1by1(comm, data, root=0):
  """Gather dictionary elements by sending them one-by-one to avoid overflow"""
  rank = comm.rank
  on_root = root == rank
  max_data_length = comm.reduce(len(data), op=MPI.MAX, root=root)
  max_data_length = comm.bcast(max_data_length, root=root)
  data_list = list(data.items()) + [None] * max_data_length
  received = [None] * max_data_length * (comm.size - 1)
  for i, row in enumerate(range(max_data_length)):
    for j, source in enumerate(range(1, comm.size)):
      tag = i * (comm.size - 1) + j
      comm.barrier()
      if rank == source:
        print(f'sending from {source=} to {root=}')
        comm.send(data_list[row], dest=root, tag=tag)
      elif on_root:
        print(f'received from {source=} to {root=}')
        received.append(comm.recv(source=source, tag=tag))
  if on_root:
    data.update({r[0]: r[1] for r in received if r is not None})
  return data if on_root else None


def collect_dict_stripes(comm, data, root=0):
  """Gather dictionary elements by sending them one-by-one to avoid overflow"""
  on_root = root == comm.rank
  received = []
  max_data_length = comm.reduce(len(data), op=MPI.MAX, root=root)
  max_data_length = comm.bcast(max_data_length, root=root)
  data_list = list(data.items()) + [None] * max_data_length
  for data_row in range(max_data_length):
    gathered = comm.gather(data_list[data_row], root=root)
    if on_root:
      received.extend(g for g in gathered if g is not None)
  return {r[0]: r[1] for r in received if r is not None} if on_root else None
