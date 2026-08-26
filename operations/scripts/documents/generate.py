from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import (
    atomic_write,
    find_project_root,
    require_supported_python,
    today_iso,
)
from operations.scripts.documents.auto_generate_tasks import auto_generate_tasks
from operations.scripts.documents.index import render_index
from operations.scripts.documents.non_markdown_index import render_non_markdown_index
from operations.scripts.documents.platform_capability import render_platfrom_capability
from operations.scripts.documents.repository_tree import render_repository_structure
from operations.scripts.documents.test_catalog import render_test_catalog
from operations.scripts.documents.traceability import render_traceability
from operations.scripts.status.generate_project_status import collect_milestones
from operations.scripts.status.human_status import render_repository_project_status
from operations.scripts.tasks.generate import render_task_index


def generate_all(root: Path, generated_date: str | None = None) -> list[str]:
    date = generated_date or today_iso()
    changed: list[str] = []

    # Auto-generate TASK documents for in-scope, unimplemented components first.
    # TEST specs are not auto-generated: writing them requires a real evidence
    # source (automated_evidence/manual_evidence) that only exists once the
    # requirement is actually implemented — see TASK template step "написать тесты".
    changed.extend(auto_generate_tasks(root))

    # repository_structure.md scans the filesystem for every tracked-style
    # file (including the other generated outputs and itself), so it must be
    # rendered and written last - after every other output below has already
    # landed on disk. Rendering it earlier would snapshot a file listing one
    # generation cycle stale whenever a new generated file is introduced.
    outputs = [
        (root / "tasks.md", render_task_index(root, date)),
        (root / "project_status.md", render_repository_project_status(root)),
        (root / "generated" / "markdown_index.md", render_index(root, date)),
        (root / "generated" / "non_markdown_index.md", render_non_markdown_index(root, date)),
        (root / "generated" / "traceability_matrix.md", render_traceability(root, date)),
        (root / "generated" / "test_catalog.md", render_test_catalog(root, date)),
        (root / "generated" / "platfrom_capability.md", render_platfrom_capability(root, date)),
    ]
    for path, rendered in outputs:
        if atomic_write(path, rendered):
            changed.append(path.relative_to(root).as_posix())

    # Remove semantic_review_v1.md when moving past m01
    current_milestone = collect_milestones(root)["current"]
    current_id = str(current_milestone["id"])
    semantic_review = root / "semantic_review_v1.md"
    if semantic_review.exists() and current_id != "m01":
        semantic_review.unlink()
        changed.append(semantic_review.relative_to(root).as_posix())

    repository_structure_path = root / "generated" / "repository_structure.md"
    if atomic_write(repository_structure_path, render_repository_structure(root, date)):
        changed.append(repository_structure_path.relative_to(root).as_posix())

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
