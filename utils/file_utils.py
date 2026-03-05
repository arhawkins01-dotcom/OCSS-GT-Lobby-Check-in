from __future__ import annotations
import os
from datetime import datetime

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def timestamped_filename(prefix: str, ext: str="csv") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.{ext}"
