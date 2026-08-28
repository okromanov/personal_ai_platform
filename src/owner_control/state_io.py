"""Fail-closed, atomic JSON persistence for owner-control state."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _fsync_parent_directory(path: Path) -> None:
    """Persist the directory entry created by ``os.replace`` on POSIX.

    Windows does not expose a portable directory-fsync primitive through
    Python. There ``os.replace`` retains the platform's documented semantics;
    POSIX filesystems get the additional directory durability barrier.
    """
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_fd = os.open(path.parent, flags)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def read_json_object(path: Path) -> dict[str, Any]:
    """Read a JSON object; callers decide whether a missing file is valid."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"cannot read trusted state from {path.name}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"trusted state in {path.name} must be a JSON object")
    return raw


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Durably replace one JSON state file without exposing partial content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        _fsync_parent_directory(path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
