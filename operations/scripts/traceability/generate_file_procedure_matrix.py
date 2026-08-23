#!/usr/bin/env python3
"""
Auto-generate file/procedure traceability matrix from project structure.

Analyzes:
- work/tasks/*.md - task definitions
- work/tests/*.md - test specifications
- work/m*/ - milestone folders
- operations/scripts/ - automation procedures
- .claude/skills/pre_commit_hook.sh - available hooks

Generates: generated/file_procedure_traceability_matrix.md
"""

import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


def parse_yaml_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter fields"""
    match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    fields = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def collect_files(root_path: str | Path | None = None) -> dict:
    """Collect all tracked files and their metadata"""
    files: dict[str, Any] = defaultdict(dict)
    root = Path(root_path) if root_path else Path(".")

    try:
        # Collect TASK files
        work_tasks = root / "work" / "tasks"
        if work_tasks.exists():
            for task_file in work_tasks.glob("*.md"):
                try:
                    meta = parse_yaml_frontmatter(task_file.read_text(encoding="utf-8"))
                    if meta.get("id"):
                        depends_on_str = meta.get("depends_on", "")
                        tests_str = meta.get("tests", "")
                        files["tasks"][meta["id"]] = {
                            "path": str(task_file),
                            "work_state": meta.get("work_state"),
                            "depends_on": depends_on_str.split(",") if depends_on_str else [],
                            "tests": tests_str.split(",") if tests_str else [],
                        }
                except Exception as e:
                    print(
                        f"WARNING: Failed to parse {task_file}: {e}",
                        file=sys.stderr,
                    )
                    continue

        # Collect TEST files
        work_tests = root / "work" / "tests"
        if work_tests.exists():
            for test_file in work_tests.glob("*.md"):
                try:
                    meta = parse_yaml_frontmatter(test_file.read_text(encoding="utf-8"))
                    if meta.get("id"):
                        traces_to_str = meta.get("traces_to", "")
                        files["tests"][meta["id"]] = {
                            "path": str(test_file),
                            "execution": meta.get("execution"),
                            "traces_to": traces_to_str.split(",") if traces_to_str else [],
                        }
                except Exception as e:
                    print(
                        f"WARNING: Failed to parse {test_file}: {e}",
                        file=sys.stderr,
                    )
                    continue

        # Collect milestone files
        work_dir = root / "work"
        if work_dir.exists():
            for milestone_dir in work_dir.glob("m[0-9]*"):
                milestone_id = milestone_dir.name
                files["milestones"][milestone_id] = {
                    "path": str(milestone_dir),
                    "files": list(milestone_dir.glob("*.md")),
                }
    except Exception as e:
        print(f"WARNING: Failed to collect files: {e}", file=sys.stderr)

    return files


def generate_matrix(files: dict) -> str:
    """Generate markdown matrix document"""
    today = date.today().isoformat()

    matrix = f"""<!-- generated file: do not edit manually -->
---
id: file_procedure_traceability_matrix_generated
type: generated_traceability_matrix
generation_state: generated
version: 1.0
created: {today}
updated: {today}
---

# File and Procedure Traceability Matrix (Auto-generated)

> Automatic matrix of file state transitions and their dependencies.
> Regenerated on each CI run from actual project structure.
> Manual matrix kept at: See `work/procedures/` for detailed procedures documentation

## Task → Test → Component Linkage

| Task | State | Test | Test Status | Component |
|---|---|---|---|---|
"""

    for task_id in sorted(files.get("tasks", {}).keys()):
        task = files["tasks"][task_id]
        test_ids = task.get("tests", [])
        component = task.get("work_state", "?")

        for test_id in test_ids:
            test_info = files.get("tests", {}).get(test_id, {})
            test_exec = test_info.get("execution", "unknown")
            matrix += f"| {task_id} | {component} | {test_id} | {test_exec} | — |\n"

    matrix += f"""
## State Transition Timeline

| Event | Files Updated | When |
|---|---|---|
| Task created | `work/tasks/taskXXX.md` created | `work_state: planned` |
| Task started | `work/tasks/taskXXX.md` updated | `work_state: in-progress`, `next_actor: agent` |
| Task completed | Multiple files | `work_state: completed`, dashboards regenerated |
| Test added | `work/tests/testXXX.md` created | `execution: automated` |
| Milestone transition | `work/m0X/*` files created | state change triggered |

## Automation Hooks

| Trigger | Script | Action | Output |
|---|---|---|---|
| Pre-commit | `pre_commit_regenerate_dashboards.sh` | Regenerate dashboards if task files changed | project_status.md, tasks.md |
| Pre-commit | `increment_file_version.py` | Auto-increment version field | All .md files updated |
| File modified | `increment_file_version.py` | Increment version semver | major.minor → major.(minor+1) |
| CI runs | `generate_project_status.py` | Full dashboard regeneration | project_status.md |
| CI runs | `generate.py --all` | Generate all derived docs | tasks.md, generated/* |

## Milestone Auto-init

```bash
python3 operations/scripts/milestones/init_milestone.py m0X
```

Creates:
- `work/m0X/owner_checklist.md` - acceptance checklist
- `work/m0X/semantic_review.md` - review procedure
- `work/m0X/final_report.md` - completion report

---

*Last generated: {today}*
*This is an auto-generated file. See work/procedures/ for detailed procedures documentation.*
"""

    return matrix


def generate_file_procedure_matrix(root_path=None) -> bool:
    """Generate and write the traceability matrix. Returns True if file changed."""
    try:
        root = Path(root_path) if root_path else Path(".")
        files = collect_files(root)
        matrix = generate_matrix(files)

        output_path = root / "generated" / "file_procedure_traceability_matrix.md"
        output_path.parent.mkdir(exist_ok=True)

        existing = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        if existing == matrix:
            return False

        output_path.write_text(matrix, encoding="utf-8")
        return True
    except Exception as e:
        print(
            f"ERROR: Failed to generate traceability matrix: {e}",
            file=sys.stderr,
        )
        return False


if __name__ == "__main__":
    if generate_file_procedure_matrix():
        print("✓ Generated generated/file_procedure_traceability_matrix.md")
    else:
        print("✓ Generated file is up to date")
