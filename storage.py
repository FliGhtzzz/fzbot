"""Thread-safe JSON transactions and atomic file replacement for one bot process."""
import copy
import json
import os
import tempfile
from functools import wraps
from threading import RLock
from data_paths import data_path

lock = RLock()


def read_json(filename, default):
    with lock:
        try:
            with open(data_path(filename), encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return copy.deepcopy(default)


def write_json(filename, data):
    with lock:
        destination = data_path(filename)
        fd, temporary = tempfile.mkstemp(dir=os.path.dirname(destination), prefix=".json-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def synchronized(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with lock:
            return function(*args, **kwargs)
    return wrapped
