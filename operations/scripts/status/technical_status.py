from __future__ import annotations

from pathlib import Path

from operations.scripts.common.project import atomic_write, now_iso_minutes, today_iso
from operations.scripts.status.generate_project_status import (
    build_progress_snapshot,
    render_progress_sections,
)


def generate_technical_status(
    root: Path,
    *,
    check_summary: dict[str, object],
    test_returncode: int,
    test_output: str,
    git: dict[str, object],
) -> Path:
    snapshot = build_progress_snapshot(
        root,
        check_summary=check_summary,
        test_returncode=test_returncode,
        test_output=test_output,
        git=git,
    )
    path = root / "runtime" / "technical_status.md"
    atomic_write(
        path,
        f"""---
id: technical_status_{str(git.get("commit", "unknown"))[:12]}
type: runtime_status
generation_state: generated
version: 1.0
generated: {today_iso()}
updated_at: {now_iso_minutes()}
acceptance_state: {snapshot["acceptance"]["state"]}
---

# Технический статус текущей редакции Git

> Автоматический результат проверок конкретной редакции Git. Он не меняет проектное состояние в `project_status.md`.

{render_progress_sections(snapshot)}
""",
    )
    return path
