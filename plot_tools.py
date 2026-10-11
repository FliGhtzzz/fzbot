"""Matplotlib pyplot uses shared state; serialize rendering in worker threads."""
from functools import wraps
from threading import RLock

_lock = RLock()


def serialized_plot(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with _lock:
            return function(*args, **kwargs)
    return wrapped
