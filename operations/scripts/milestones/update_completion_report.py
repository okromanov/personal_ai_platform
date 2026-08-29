#!/usr/bin/env python3
"""
Render and update work/acceptance/m0X_final_report.md from real repository state.

Unlike a hand-filled template, every section here is computed: which files
were actually added/changed since the milestone started, which TASK/TEST
cards belong to it and what each delivered, which requirements it covers,
and how much calendar time elapsed. "Известные ограничения" and
"Рекомендации" are the only sections requiring an owner/agent's own
judgment: they stay as placeholders until filled in by hand, and once
filled in are preserved verbatim across every later regeneration.

Usage: python3 operations/scripts/milestones/update_completion_report.py m01
"""

from __future__ import annotations

import posixpath
import re
import sys
from datetime import date
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import run_command
from operations.scripts.common.status_types import MilestoneItem, TaskItem
from operations.scripts.documents.template_contracts import (
    assert_registered_output,
    render_contract,
)
from operations.scripts.documents.traceability import collect_traceable_elements
from operations.scripts.status.generate_project_status import collect_milestones
from operations.scripts.tasks.generate import collect_tasks

RESULT_SECTION = re.compile(r"(?ms)^##\s+(?:\d+\.\s*)?Результат\s*$\n(.*?)(?=^##\s|\Z)")
EXCLUDED_DIFF_PREFIXES = ("runtime/",)


def _link(target_path: str) -> str:
    """Repo-root-relative path (optionally with a #anchor) rewritten relative
    to work/, where final_report.md itself lives."""
    path_part, sep, anchor = target_path.partition("#")
    relative = posixpath.relpath(path_part, start="work/acceptance")
    return f"{relative}{sep}{anchor}"


def _path_reference(root: Path, path: str) -> str:
    """Markdown link for `path` if it still exists at HEAD, else plain code.

    A historical git diff can name a file that was later renamed or removed
    (e.g. a TASK file renumbered after this milestone finished); linking to a
    path that no longer exists on disk would just be a broken link.
    """
    if (root / path).exists():
        return f"[`{path}`]({_link(path)})"
    return f"`{path}` (путь изменился или файл удалён позже)"


def _milestone_item(root: Path, milestone_id: str) -> MilestoneItem | None:
    for item in collect_milestones(root)["items"]:
        if str(item["id"]).lower() == milestone_id.lower():
            return item
    return None


def _shallow_boundary_commits(root: Path) -> set[str]:
    """SHA-1s of commits at the edge of a shallow clone (empty in a full clone).

    Git records these in .git/shallow: commits it has, but whose parents it
    does not. At that boundary, `git log --diff-filter=A` shows every file as
    "just added" and `git show <sha>:path` shows whatever state existed there
    as if it were the earliest — indistinguishable from genuinely being the
    first commit. A result that lands exactly on one of these SHAs cannot be
    trusted; a result elsewhere in history is unaffected by the boundary.
    """
    shallow_file = root / ".git" / "shallow"
    if not shallow_file.is_file():
        return set()
    return {
        line.strip()
        for line in shallow_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def _earliest_add(root: Path, path: str) -> tuple[str, str] | None:
    """(sha, date) of the earliest commit that added `path`, or None."""
    result = run_command(
        ["git", "log", "--diff-filter=A", "--format=%H %ad", "--date=short", "--", path],
        cwd=root,
    )
    lines = [line for line in result.stdout.strip().splitlines() if line]
    if not lines:
        return None
    sha, commit_date = lines[-1].split(" ", 1)
    return sha, commit_date


def _milestone_start(root: Path, milestone_id: str) -> tuple[str, str] | None:
    """(sha, date) of the commit that first created this milestone's final_report.md.

    Returns None both when no such commit is found and when the only match is
    a shallow-clone boundary commit — in the latter case the file may really
    have been added earlier, before the point history was cut off.

    Checks both the current flat path and the legacy work/{id}/final_report.md
    path (retired when reports moved to work/ directly) and keeps the earlier
    of the two: relying on `git log --follow`'s rename-similarity heuristic
    instead would silently break whenever the rename and a content edit land
    in the same commit (e.g. a GitHub squash merge combining several commits
    into one) and git no longer considers the two sides similar enough to
    call it a rename.
    """
    candidates = [
        candidate
        for candidate in (
            _earliest_add(root, f"work/acceptance/{milestone_id}_final_report.md"),
            _earliest_add(root, f"work/{milestone_id}_final_report.md"),
            _earliest_add(root, f"work/{milestone_id}/final_report.md"),
        )
        if candidate is not None
    ]
    if not candidates:
        return None
    sha, commit_date = min(candidates, key=lambda candidate: candidate[1])
    if sha in _shallow_boundary_commits(root):
        return None
    return sha, commit_date


def _milestone_completion_commit(root: Path, milestone_id: str) -> tuple[str, str] | None:
    """(sha, date) of the earliest commit where milestones.md first records
    this milestone's own section as work_state: `completed`.

    Using "now" (HEAD) as the diff endpoint would fold every later, unrelated
    commit into an already-finished milestone's report. Walking history to the
    actual completion commit keeps the report scoped to what that milestone
    delivered. If the earliest available commit already shows "completed" and
    that commit is a shallow-clone boundary, the real completion commit may be
    further back than local history reaches — treated as not found rather than
    silently accepted.
    """
    result = run_command(
        ["git", "log", "--reverse", "--format=%H %ad", "--date=short", "--", "milestones.md"],
        cwd=root,
    )
    section_pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(milestone_id)}\b.*?(?=^##\s|\Z)", re.IGNORECASE
    )
    boundary_commits = _shallow_boundary_commits(root)
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        sha, commit_date = line.split(" ", 1)
        content = run_command(["git", "show", f"{sha}:milestones.md"], cwd=root).stdout
        match = section_pattern.search(content)
        if match and "work_state: `completed`" in match.group(0):
            if sha in boundary_commits:
                return None
            return sha, commit_date
    return None


def _git_file_changes(root: Path, base_sha: str, head_sha: str) -> tuple[list[str], list[str]]:
    """(added, modified) paths between base and head, excluding derived output."""
    result = run_command(["git", "diff", "--name-status", f"{base_sha}..{head_sha}"], cwd=root)
    added: list[str] = []
    modified: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        if path.startswith(EXCLUDED_DIFF_PREFIXES):
            continue
        if status.startswith("A"):
            added.append(path)
        elif status.startswith(("M", "R")):
            modified.append(path)
    return sorted(added), sorted(modified)


def _milestone_tasks(tasks: list[TaskItem], milestone_id: str) -> list[TaskItem]:
    return [
        task
        for task in tasks
        if milestone_id.lower() in {value.lower() for value in task["traces_to"]}
    ]


def _deliverable_paths(task: TaskItem) -> list[str]:
    own_path = str(task["path"])
    return [path for path in task.get("allowed_paths", []) if path != own_path]


def _result_section(body: str) -> str:
    match = RESULT_SECTION.search(body)
    return match.group(1).strip() if match else ""


def _requirement_links(root: Path, scope: list[str]) -> list[str]:
    records = collect_traceable_elements(root)
    links = []
    for identifier in scope:
        record = records.get(identifier.upper())
        if record is None:
            links.append(f"`{identifier}`")
            continue
        target = _link(f"{record['path']}#{record['anchor']}")
        links.append(f"[`{identifier}`]({target})")
    return links


_LIMITATIONS_HEADING = "6. Известные ограничения"
_RECOMMENDATIONS_HEADING = "7. Рекомендации для следующего этапа"
_UNFILLED_PLACEHOLDER = "(заполняется при завершении этапа)"


def _existing_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _preserved_or_placeholder(root: Path, milestone_id: str, heading: str) -> str:
    """A hand-filled "Известные ограничения"/"Рекомендации" section must
    survive every regeneration verbatim: these two are the only sections
    render_final_report cannot compute from repository state, so once an
    owner/agent has filled them in, re-running this function must not
    silently wipe that judgment back to the placeholder.
    """
    path = root / "work" / "acceptance" / f"{milestone_id}_final_report.md"
    if not path.is_file():
        return _UNFILLED_PLACEHOLDER
    existing = _existing_section(path.read_text(encoding="utf-8"), heading)
    return existing if existing and existing != _UNFILLED_PLACEHOLDER else _UNFILLED_PLACEHOLDER


def _time_span(start: str, end: str) -> str:
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days
    if days <= 0:
        return f"{start} (в тот же день)"
    return f"{start} — {end} ({days} дн.)"


def render_final_report(root: Path, milestone_id: str) -> str:
    milestone = _milestone_item(root, milestone_id)
    if milestone is None:
        raise ValueError(f"Неизвестный этап: {milestone_id}")

    completed = milestone["work_state"] == "completed"
    today = date.today().isoformat()
    start = _milestone_start(root, milestone_id)
    start_date = start[1] if start else today

    tasks_report = collect_tasks(root)
    milestone_tasks = _milestone_tasks(tasks_report["tasks"], milestone_id)
    completed_tasks = [task for task in milestone_tasks if task["work_state"] == "completed"]
    if not milestone_tasks:
        all_tasks_done_text = "не применимо (TASK для этапа не создаются)"
    elif len(completed_tasks) == len(milestone_tasks):
        all_tasks_done_text = "да"
    else:
        all_tasks_done_text = "нет"

    completion = _milestone_completion_commit(root, milestone_id) if completed else None
    if completed and (start is None or completion is None):
        raise ValueError(
            f"{milestone_id}: work_state завершено, но локальная история Git не содержит "
            "коммит начала или завершения этапа (мелкий чекаут?). Нужен полный git fetch, "
            "иначе отчёт будет молча неверным."
        )
    if completed and start is not None and completion is not None:
        end_sha, end_date = completion
        added, modified = _git_file_changes(root, start[0], end_sha)
        time_line = _time_span(start_date, end_date)
        completion_date = end_date
    else:
        added, modified = [], []
        time_line = f"{start_date} — продолжается"
        completion_date = "—"

    completion_section = "\n".join(
        [
            f"- Статус: {'завершено' if completed else 'в процессе'}",
            f"- Дата начала: {start_date}",
            f"- Дата завершения: {completion_date}",
            f"- Время работы над этапом: {time_line}",
            f"- Все задачи завершены: {all_tasks_done_text}",
        ]
    )

    functional_lines: list[str] = []
    result_text = milestone["result"]
    if result_text:
        milestones_link = _link("milestones.md")
        functional_lines.append(
            f"**Цель этапа (из [`milestones.md`]({milestones_link})):** {result_text}"
        )
        functional_lines.append("")
    if not completed_tasks:
        functional_lines.append("Пока ни одна TASK этого этапа не завершена.")
    else:
        for task in completed_tasks:
            component = str(task.get("component", "")) or "—"
            task_result = _result_section(str(task["body"])) or "_Раздел «Результат» пуст._"
            functional_lines.extend(
                [
                    f"### `{component}` — {task['title']} (`{task['id']}`)",
                    "",
                    task_result,
                    "",
                ]
            )
    functional_section = "\n".join(functional_lines).rstrip()

    changes_lines: list[str] = []
    if not completed:
        changes_lines.append("Считается при завершении этапа (сравнение с коммитом начала этапа).")
    elif not added and not modified:
        changes_lines.append("Изменений файлов не обнаружено.")
    else:
        current_added = [path for path in added if (root / path).exists()]
        current_modified = [path for path in modified if (root / path).exists()]
        changes_lines.extend([f"### Новые файлы ({len(current_added)})", ""])
        changes_lines.extend(
            (f"- {_path_reference(root, path)}" for path in current_added)
            if current_added
            else ["—"]
        )
        changes_lines.extend(["", f"### Изменённые файлы ({len(current_modified)})", ""])
        changes_lines.extend(
            (f"- {_path_reference(root, path)}" for path in current_modified)
            if current_modified
            else ["—"]
        )
    changes_section = "\n".join(changes_lines).rstrip()

    task_lines: list[str] = []
    if not milestone_tasks:
        task_lines.append("Проектных TASK для этого этапа нет.")
    else:
        task_lines.extend(["| TASK | Компонент | Статус | TEST |", "|---|---|---|---|"])
        for task in milestone_tasks:
            tests = (
                ", ".join(
                    f"[`{test['id']}`]({_link(str(test['path']))})"
                    for test in task.get("tests", [])
                )
                or "—"
            )
            task_link = _link(str(task["path"]))
            task_lines.append(
                f"| [`{task['id']}`]({task_link}) | "
                f"`{task.get('component', '') or '—'}` | {task['work_state']} | {tests} |"
            )
    tasks_section = "\n".join(task_lines)

    scope = milestone.get("scope", [])
    requirements_section = ", ".join(_requirement_links(root, scope)) if scope else "—"

    return render_contract(
        root,
        "milestone_completion_report",
        {
            "milestone_id": milestone_id,
            "completion_state": "completed" if completed else "pending",
            "created": start_date,
            "updated": today,
            "milestone_label": milestone_id.upper(),
            "completion_section": completion_section,
            "functional_section": functional_section,
            "changes_section": changes_section,
            "tasks_section": tasks_section,
            "requirements_section": requirements_section,
            "limitations_section": _preserved_or_placeholder(
                root, milestone_id, _LIMITATIONS_HEADING
            ),
            "recommendations_section": _preserved_or_placeholder(
                root, milestone_id, _RECOMMENDATIONS_HEADING
            ),
        },
    )


def update_completion_report(milestone_id: str, root: Path | None = None) -> bool:
    """Regenerate work/acceptance/m0X_final_report.md from current repository state."""
    if root is None:
        root = Path.cwd()

    report_path = root / "work" / "acceptance" / f"{milestone_id}_final_report.md"
    if not report_path.exists():
        return False

    try:
        assert_registered_output(root, "milestone_completion_report", report_path)
        report_path.write_text(render_final_report(root, milestone_id), encoding="utf-8")
        return True
    except Exception as e:
        print(f"ERROR: Failed to update {milestone_id} final_report: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python3 operations/scripts/milestones/update_completion_report.py <milestone_id>"
        )
        sys.exit(1)

    milestone_id = sys.argv[1]
    if update_completion_report(milestone_id):
        print(f"✓ Updated {milestone_id} final_report.md")
        sys.exit(0)
    else:
        print(f"✗ Failed to update {milestone_id}")
        sys.exit(1)
