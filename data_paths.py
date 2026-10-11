"""Runtime storage; defaults to the project directory outside Docker."""
import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def data_path(filename: str) -> str:
    return str(DATA_DIR / filename)
