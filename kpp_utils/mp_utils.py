def bcast_dict_1by1(comm, data, root=0):
  """Broadcast dictionary elements one-by-one to avoid MPI overflow issues"""
  received = {}
  for key, value in data.items():
    received[key] = comm.bcast(value, root=root)
  return received


def gather_dict_1by1(comm, data, root=0):
  """Gather dictionary elements by sending them one-by-one to avoid overflow"""
  rank = comm.rank
  received = {}
  key_rank_map = {key: rank for key in data.keys()}
  key_rank_map = comm.bcast(key_rank_map, root=root)
  for key, source in key_rank_map.items():
    if rank == source:
        comm.Send(data[key], dest=root)
    if rank == root:
        received[key] = comm.recv(source=source)
  return received
