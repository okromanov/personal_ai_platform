#!/usr/bin/env python3
"""
Render and update work/m0X_final_report.md from real repository state.

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
from operations.scripts.documents.traceability import collect_traceable_elements
from operations.scripts.status.generate_project_status import collect_milestones
from operations.scripts.tasks.generate import collect_tasks

RESULT_SECTION = re.compile(r"(?ms)^##\s+(?:\d+\.\s*)?Результат\s*$\n(.*?)(?=^##\s|\Z)")
EXCLUDED_DIFF_PREFIXES = ("generated/",)


def _link(target_path: str) -> str:
    """Repo-root-relative path (optionally with a #anchor) rewritten relative
    to work/, where final_report.md itself lives."""
    path_part, sep, anchor = target_path.partition("#")
    relative = posixpath.relpath(path_part, start="work")
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


def _milestone_start(root: Path, milestone_id: str) -> tuple[str, str] | None:
    """(sha, date) of the commit that first created this milestone's final_report.md.

    Returns None both when no such commit is found and when the only match is
    a shallow-clone boundary commit — in the latter case the file may really
    have been added earlier, before the point history was cut off. `--follow`
    keeps this pointed at the true creation commit across the file's later
    rename from work/{id}/final_report.md to work/{id}_final_report.md.
    """
    result = run_command(
        [
            "git",
            "log",
            "--follow",
            "--diff-filter=A",
            "--format=%H %ad",
            "--date=short",
            "--",
            f"work/{milestone_id}_final_report.md",
        ],
        cwd=root,
    )
    lines = [line for line in result.stdout.strip().splitlines() if line]
    if not lines:
        return None
    sha, commit_date = lines[-1].split(" ", 1)
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
    path = root / "work" / f"{milestone_id}_final_report.md"
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
    completed_tasks = [t for t in milestone_tasks if t["work_state"] == "completed"]
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

    lines = [
        "---",
        f"id: {milestone_id}_final_report",
        "type: milestone_completion_report",
        f"completion_state: {'completed' if completed else 'pending'}",
        "version: 1.0",
        f"created: {start_date}",
        f"updated: {today}",
        f"milestone: {milestone_id}",
        "---",
        "",
        f"# {milestone_id.upper()} — Итоговый отчёт",
        "",
        "## 1. Состояние завершения",
        "",
        f"- Статус: {'завершено' if completed else 'в процессе'}",
        f"- Дата начала: {start_date}",
        f"- Дата завершения: {completion_date}",
        f"- Время работы над этапом: {time_line}",
        f"- Все задачи завершены: {all_tasks_done_text}",
        "",
        "## 2. Что реализовано функционально",
        "",
    ]
    result_text = milestone["result"]
    if result_text:
        milestones_link = _link("milestones.md")
        lines.append(f"**Цель этапа (из [`milestones.md`]({milestones_link})):** {result_text}")
        lines.append("")
    if not completed_tasks:
        lines.append("Пока ни одна TASK этого этапа не завершена.")
        lines.append("")
    else:
        for task in completed_tasks:
            component = str(task.get("component", "")) or "—"
            result_text = _result_section(str(task["body"])) or "_Раздел «Результат» пуст._"
            lines.append(f"### `{component}` — {task['title']} (`{task['id']}`)")
            lines.append("")
            lines.append(result_text)
            lines.append("")
    lines.append("## 3. Изменения в репозитории")
    lines.append("")
    if not completed:
        lines.append("Считается при завершении этапа (сравнение с коммитом начала этапа).")
        lines.append("")
    elif not added and not modified:
        lines.append("Изменений файлов не обнаружено.")
        lines.append("")
    else:
        lines.append(f"### Новые файлы ({len(added)})")
        lines.append("")
        lines.extend((f"- {_path_reference(root, path)}" for path in added) if added else ["—"])
        lines.append("")
        lines.append(f"### Изменённые файлы ({len(modified)})")
        lines.append("")
        lines.extend(
            (f"- {_path_reference(root, path)}" for path in modified) if modified else ["—"]
        )
        lines.append("")
    lines.append("## 4. Задачи и тесты этапа")
    lines.append("")
    if not milestone_tasks:
        lines.append("Проектных TASK для этого этапа нет.")
    else:
        lines.append("| TASK | Компонент | Статус | TEST |")
        lines.append("|---|---|---|---|")
        for task in milestone_tasks:
            tests = (
                ", ".join(f"[`{t['id']}`]({_link(str(t['path']))})" for t in task.get("tests", []))
                or "—"
            )
            task_link = _link(str(task["path"]))
            lines.append(
                f"| [`{task['id']}`]({task_link}) | `{task.get('component', '') or '—'}` "
                f"| {task['work_state']} | {tests} |"
            )
    lines.append("")
    lines.append("## 5. Связанные требования")
    lines.append("")
    scope = milestone.get("scope", [])
    lines.append(", ".join(_requirement_links(root, scope)) if scope else "—")
    lines.append("")
    lines.append(f"## {_LIMITATIONS_HEADING}")
    lines.append("")
    lines.append(_preserved_or_placeholder(root, milestone_id, _LIMITATIONS_HEADING))
    lines.append("")
    lines.append(f"## {_RECOMMENDATIONS_HEADING}")
    lines.append("")
    lines.append(_preserved_or_placeholder(root, milestone_id, _RECOMMENDATIONS_HEADING))
    lines.append("")
    return "\n".join(lines)


def update_completion_report(milestone_id: str, root: Path | None = None) -> bool:
    """Regenerate work/m0X_final_report.md from current repository state."""
    if root is None:
        root = Path.cwd()

    report_path = root / "work" / f"{milestone_id}_final_report.md"
    if not report_path.exists():
        return False

    try:
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
