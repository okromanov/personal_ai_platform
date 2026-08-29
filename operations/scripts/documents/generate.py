from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import (
    atomic_write_generated,
    find_project_root,
    require_supported_python,
)
from operations.scripts.documents.template_contracts import assert_registered_output
from operations.scripts.status.generate_project_status import collect_milestones
from operations.scripts.status.human_status import render_repository_project_status


def generate_all(root: Path, _generated_date: str | None = None) -> list[str]:
    changed: list[str] = []
    outputs = [
        (root / "project_status.md", render_repository_project_status(root)),
    ]
    for path, rendered in outputs:
        assert_registered_output(root, "project_status", path)
        if atomic_write_generated(path, rendered):
            changed.append(path.relative_to(root).as_posix())

    # Remove semantic_review_v1.md when moving past m01
    current_milestone = collect_milestones(root)["current"]
    current_id = str(current_milestone["id"])
    semantic_review = root / "semantic_review_v1.md"
    if semantic_review.exists() and current_id != "m01":
        semantic_review.unlink()
        changed.append(semantic_review.relative_to(root).as_posix())

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Генерация производных файлов")
    parser.add_argument("--all", action="store_true")
    parser.parse_args()
    require_supported_python()
    root = find_project_root(Path.cwd())
    changed = generate_all(root)
    print("Обновлены файлы:" if changed else "Производные файлы уже актуальны.")
    for path in changed:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
