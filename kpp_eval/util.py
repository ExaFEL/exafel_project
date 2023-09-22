from functools import wraps
import os
from typing import Callable


def set_default_return(default_path: str) -> Callable:
  """Decorate func so that None return is replaced with default_path instead"""
  def decorator(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
      result = func(*args, **kwargs)
      return os.path.expandvars(default_path) if result is None else result
    return wrapper
  return decorator
