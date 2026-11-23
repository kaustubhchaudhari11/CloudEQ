"""Minimal ``.env`` loader shared by the command-line entry points."""

import os
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> int:
    """Copy ``KEY=VALUE`` lines into ``os.environ`` without overriding real variables."""

    target = Path(path)
    if not target.is_file():
        return 0
    loaded = 0
    for line in target.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            loaded += 1
    return loaded
