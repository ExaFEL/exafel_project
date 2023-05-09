from libtbx.mpi4py import MPI


def bcast_dict_1by1(comm, data, root=0):
  """Broadcast dictionary elements one-by-one to avoid MPI overflow issues"""
  on_root = root == comm.rank
  received = {}
  keys = list(data.keys()) if data is not None else None
  keys = comm.bcast(keys, root=root)
  for key in keys:
    value = data[key] if on_root else None
    received[key] = comm.bcast(value, root=root)
  return received


def collect_dict_1by1_alt(comm, data, root=0):
  """Gather dictionary elements by sending them one-by-one to avoid overflow"""
  on_root = root == comm.rank
  received = []
  max_data_length = comm.reduce(len(data), op=MPI.MAX, root=root)
  max_data_length = comm.bcast(max_data_length, root=root)
  data_list = list(data.items()) + [None] * max_data_length
  for data_row in range(max_data_length):
    for source in range(comm.size):
      comm.barrier()
      print(f'sending from {source=} to {root=}')
      recv = comm.sendrecv(data_list[data_row], dest=root, source=source)
      if on_root and recv is not None:
        received.append(recv)
  return {r[0]: r[1] for r in received if r is not None} if on_root else None


def collect_dict_1by1(comm, data, root=0):
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
