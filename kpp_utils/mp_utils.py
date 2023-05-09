def bcast_dict_1by1(comm, data, root=0):
  """Broadcast dictionary elements one-by-one to avoid MPI overflow issues"""
  print(f'bcast: {comm.rank=}, {data.items()}')
  received = {}
  for key, value in data.items():
    received[key] = comm.bcast([value], root=root)[0]
  print(f'bcast: {comm.rank=}, {received.items()}')
  return received


def gather_dict_1by1(comm, data, root=0):
  """Gather dictionary elements by sending them one-by-one to avoid overflow"""
  rank = comm.rank
  print(f'bcast: {rank=}, {data.items()}')
  received = {}
  key_rank_map = {key: rank for key in data.keys()}
  key_rank_map = comm.bcast(key_rank_map, root=root)
  for key, source in key_rank_map.items():
    received[key] = comm.sendrecv(data[key], dest=root, source=source)
  print(f'gather: {rank=}, {received.items()}')
  return received
