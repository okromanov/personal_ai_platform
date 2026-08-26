from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

PROJECT_NAME = "personal_ai_platform"
# ADR_001 требует Python 3.12+ (стабильная версия для CI и production).
# Локально можно 3.12, 3.13 или 3.14. Hook автоматически найдёт доступный Python.
REQUIRED_PYTHON = (3, 12)
IGNORED_DIRS = {
    ".git",
    ".venv",
    ".idea",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "runtime",
}
IGNORED_FILES = {".ds_store", "thumbs.db", "settings.local.json"}


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def require_supported_python() -> None:
    if sys.version_info[:2] < REQUIRED_PYTHON:
        required = ".".join(str(part) for part in REQUIRED_PYTHON)
        actual = platform.python_version()
        raise SystemExit(
            f"Требуется Python {required}+ по ADR_001, запущен {actual}. "
            "Локальный прогон на более старой версии не совпадает с серверной проверкой."
        )


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".gitignore").exists() and (candidate / "operations" / "scripts").is_dir():
            return candidate
    raise RuntimeError(
        "Не найден корень personal_ai_platform. Запускайте команду из папки проекта."
    )


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: файл не в UTF-8 ({exc})") from exc


_REPLACE_RETRY_ATTEMPTS = 5
_REPLACE_RETRY_DELAY_SECONDS = 0.05


def _replace_with_retry(temp_name: str, path: Path) -> None:
    """os.replace() onto an actively-read/written destination can raise a
    transient PermissionError on Windows (no POSIX-style rename-over-open-
    handle guarantee there); a brief bounded retry absorbs that without
    changing behavior on POSIX, where the first attempt always succeeds."""
    for attempt in range(_REPLACE_RETRY_ATTEMPTS):
        try:
            os.replace(temp_name, path)
            return
        except PermissionError:
            if attempt == _REPLACE_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(_REPLACE_RETRY_DELAY_SECONDS)


def atomic_write(path: Path, content: str) -> bool:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    old = read_text(path) if path.exists() else None
    if old == normalized:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
        ) as handle:
            temp_name = handle.name
            handle.write(normalized)
        _replace_with_retry(temp_name, path)
    except BaseException:
        if temp_name is not None and os.path.exists(temp_name):
            os.unlink(temp_name)
        raise
    return True

_GENERATED_AT_PATTERN = re.compile(r"(?m)^generated_at: .+\n")


def _normalized_generated_content(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return _GENERATED_AT_PATTERN.sub("", normalized)


def generated_content_matches(existing: str, rendered: str) -> bool:
    """Compare generated content while ignoring its creation snapshot."""
    return _normalized_generated_content(existing) == _normalized_generated_content(rendered)


def _with_generated_snapshot(content: str, timestamp: str) -> str:
    normalized = _normalized_generated_content(content)
    marker = "generation_state: generated\n"
    if marker not in normalized:
        return normalized
    return normalized.replace(marker, f"{marker}generated_at: {timestamp}\n", 1)


def atomic_write_generated(path: Path, content: str) -> bool:
    """Write a generated document with a stable creation timestamp."""
    existing = read_text(path) if path.exists() else None
    has_snapshot = bool(existing and _GENERATED_AT_PATTERN.search(existing))
    if existing is not None and has_snapshot and generated_content_matches(existing, content):
        return False
    return atomic_write(path, _with_generated_snapshot(content, now_iso_minutes()))


def relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _git_visible_relative_paths(root: Path) -> set[str] | None:
    """Относительные пути, которые git показал бы в дереве: отслеживаемые плюс
    неотслеживаемые, но не игнорируемые (.gitignore, .git/info/exclude).

    Локальные артефакты вроде .claude/settings.local.json или
    .claude/scheduled_tasks.lock существуют только в рабочей копии конкретной
    сессии — их не видит ни один другой клон, включая CI. Голый обход
    файловой системы этого не знает и включает их в generated/*, из-за чего
    коммит с локального клона расходится с результатом на чистом checkout.
    Возвращает None, если git недоступен (например, не git-репозиторий) —
    тогда вызывающий код возвращается к обходу файловой системы напрямую.
    """
    result = run_command(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
    )
    if not result.ok:
        return None
    return {part for part in result.stdout.split("\0") if part}


def iter_files(
    root: Path, *, suffixes: set[str] | None = None, include_generated: bool = True
) -> Iterable[Path]:
    visible = _git_visible_relative_paths(root)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        relative = path.relative_to(root).as_posix()
        if visible is not None and relative not in visible:
            continue
        if any(part.lower() in IGNORED_DIRS for part in parts):
            continue
        if parts[:3] == ("generated", "reports", "daily") and path.name != ".gitkeep":
            continue
        if path.name.lower() in IGNORED_FILES:
            continue
        if not include_generated and parts and parts[0] == "generated":
            continue
        if suffixes is not None and path.suffix.lower() not in suffixes:
            continue
        yield path


def run_command(command: Sequence[str], *, cwd: Path, timeout: int = 180) -> CommandResult:
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return CommandResult(
            tuple(command), completed.returncode, completed.stdout, completed.stderr
        )
    except FileNotFoundError as exc:
        return CommandResult(tuple(command), 127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        # text=True above means stdout/stderr are str at runtime, but
        # TimeoutExpired's own type doesn't know that call context.
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else "timeout"
        return CommandResult(tuple(command), 124, stdout, stderr)


def git_info(root: Path) -> dict[str, object]:
    inside = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=root)
    if not inside.ok:
        return {
            "available": False,
            "branch": "not-initialized",
            "commit": "none",
            "commit_short": "none",
            "dirty": False,
            "changes": [],
        }
    branch = run_command(["git", "branch", "--show-current"], cwd=root)
    commit = run_command(["git", "rev-parse", "HEAD"], cwd=root)
    status = run_command(["git", "status", "--short"], cwd=root)
    changes = [line for line in status.stdout.splitlines() if line.strip()]
    full_sha = commit.stdout.strip() if commit.ok else ""
    full_sha = full_sha or "none"
    return {
        "available": True,
        "branch": branch.stdout.strip() or "detached",
        "commit": full_sha,
        "commit_short": full_sha[:12] if full_sha != "none" else "none",
        "dirty": bool(changes),
        "changes": changes,
    }


def load_project_config(root: Path) -> dict[str, object]:
    path = root / "operations" / "project_config.json"
    if not path.is_file():
        raise ValueError("Отсутствует operations/project_config.json")
    data = json.loads(read_text(path))
    if not isinstance(data, dict):
        raise ValueError("operations/project_config.json должен быть JSON object")
    return data


def today_iso() -> str:
    return datetime.now().astimezone().date().isoformat()


def now_iso_minutes() -> str:
    return datetime.now().astimezone().replace(second=0, microsecond=0).isoformat()
