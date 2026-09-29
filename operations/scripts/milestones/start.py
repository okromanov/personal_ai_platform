"""Atomic preflight and transition from planned to in-progress."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import (
    atomic_write,
    find_project_root,
    read_text,
    require_supported_python,
    run_command,
    today_iso,
)
from operations.scripts.milestones import init_milestone
from operations.scripts.quality.registry import load_quality_registry, profiles_for_milestone
from operations.scripts.status.generate_project_status import collect_milestones
from operations.scripts.tasks.semantics import (
    milestone_test_coverage_semantic,
    validate_task_semantics,
)


def preflight_start(root: Path, milestone_id: str) -> list[str]:
    """Return every blocker without mutating the repository."""
    milestone_id = milestone_id.lower()
    state = collect_milestones(root)
    raw_items = state["items"]
    items = (
        [item for item in raw_items if isinstance(item, dict)]
        if isinstance(raw_items, list)
        else []
    )
    target_index = next(
        (index for index, item in enumerate(items) if str(item["id"]) == milestone_id), None
    )
    if target_index is None:
        return [f"Неизвестный milestone {milestone_id}"]
    target = items[target_index]
    errors: list[str] = []
    if str(target["work_state"]) != "planned":
        errors.append(
            f"{milestone_id}: старт допустим только из planned, найдено {target['work_state']}"
        )
    if target_index > 0:
        previous = items[target_index - 1]
        if str(previous["work_state"]) != "completed":
            errors.append(f"{milestone_id}: предыдущий этап {previous['id']} ещё не completed")
    registry = load_quality_registry(root)
    if not profiles_for_milestone(registry, milestone_id):
        errors.append(f"{milestone_id}: до старта требуется quality profile")
    required, covered = milestone_test_coverage_semantic(root, milestone_id)
    missing = sorted(required - covered)
    if missing:
        errors.append(
            f"{milestone_id}: TEST не покрывают полный состав этапа: {', '.join(missing)}"
        )
    errors.extend(validate_task_semantics(root, milestone_id))
    return errors


def _transition(text: str, milestone_id: str, updated: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    heading = re.compile(rf"(?m)^##\s+{re.escape(milestone_id)}\s+—\s+.+$")
    match = heading.search(normalized)
    if not match:
        raise ValueError(f"Не найден milestone {milestone_id}")
    next_heading = re.search(r"(?m)^##\s+m\d{2}\s+—\s+.+$", normalized[match.end() :])
    end = match.end() + next_heading.start() if next_heading else len(normalized)
    section = normalized[match.end() : end]
    state = re.search(r"(?m)^-\s+work_state:\s+`?([a-z-]+)`?\s*$", section)
    if not state or state.group(1) != "planned":
        raise ValueError(f"{milestone_id}: ожидается work_state planned")
    absolute_start = match.end() + state.start(1)
    absolute_end = match.end() + state.end(1)
    changed = normalized[:absolute_start] + "in-progress" + normalized[absolute_end:]
    front_end = changed.find("\n---\n", 4)
    if not changed.startswith("---\n") or front_end < 0:
        raise ValueError("milestones.md не содержит корректный front matter")
    head = changed[: front_end + 5]
    date = re.search(r"(?m)^updated:\s*([^\n]+)\s*$", head)
    if not date:
        raise ValueError("milestones.md не содержит updated")
    return head[: date.start(1)] + updated + head[date.end(1) :] + changed[front_end + 5 :]


def start_milestone(root: Path, milestone_id: str, *, dry_run: bool = True) -> list[str]:
    blockers = preflight_start(root, milestone_id)
    if blockers:
        return blockers
    if dry_run:
        return []
    branch = run_command(["git", "branch", "--show-current"], cwd=root)
    if not branch.ok or branch.stdout.strip() in {"", "main", "master"}:
        return ["Старт milestone запрещён на default branch"]
    path = root / "milestones.md"
    atomic_write(path, _transition(read_text(path), milestone_id.lower(), today_iso()))
    if not init_milestone.init_milestone(milestone_id, root):
        return [f"{milestone_id}: не удалось создать начальный final_report"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверить и начать milestone атомарно")
    parser.add_argument("--milestone", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    require_supported_python()
    root = find_project_root(Path.cwd())
    dry_run = not args.apply
    blockers = start_milestone(root, str(args.milestone), dry_run=dry_run)
    if blockers:
        for blocker in blockers:
            print(f"ERROR: {blocker}")
        return 1
    if dry_run:
        print(f"Preflight {str(args.milestone).lower()}: PASS; изменений нет.")
    else:
        print(f"Milestone {str(args.milestone).lower()} переведён в in-progress.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
