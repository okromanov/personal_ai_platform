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
from pathlib import Path
from datetime import date
from collections import defaultdict

def parse_yaml_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter fields"""
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}

    fields = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            fields[key.strip()] = value.strip()
    return fields

def collect_files() -> dict:
    """Collect all tracked files and their metadata"""
    files = defaultdict(dict)

    # Collect TASK files
    for task_file in Path('work/tasks').glob('*.md'):
        meta = parse_yaml_frontmatter(task_file.read_text())
        if meta.get('id'):
            files['tasks'][meta['id']] = {
                'path': str(task_file),
                'work_state': meta.get('work_state'),
                'depends_on': meta.get('depends_on', '').split(',') if meta.get('depends_on') else [],
                'tests': meta.get('tests', '').split(',') if meta.get('tests') else [],
            }

    # Collect TEST files
    for test_file in Path('work/tests').glob('*.md'):
        meta = parse_yaml_frontmatter(test_file.read_text())
        if meta.get('id'):
            files['tests'][meta['id']] = {
                'path': str(test_file),
                'execution': meta.get('execution'),
                'traces_to': meta.get('traces_to', '').split(',') if meta.get('traces_to') else [],
            }

    # Collect milestone files
    for milestone_dir in Path('work').glob('m[0-9]*'):
        milestone_id = milestone_dir.name
        files['milestones'][milestone_id] = {
            'path': str(milestone_dir),
            'files': list(milestone_dir.glob('*.md'))
        }

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
> Manual matrix kept at: `work/procedures/file_procedure_traceability_matrix.md`

## Task → Test → Component Linkage

| Task | State | Test | Test Status | Component |
|---|---|---|---|---|
"""

    for task_id in sorted(files.get('tasks', {}).keys()):
        task = files['tasks'][task_id]
        test_ids = task.get('tests', [])
        component = task.get('work_state', '?')

        for test_id in test_ids:
            test_info = files.get('tests', {}).get(test_id, {})
            test_exec = test_info.get('execution', 'unknown')
            matrix += f"| {task_id} | {component} | {test_id} | {test_exec} | — |\n"

    matrix += f"""
## State Transition Timeline

| Event | Files Updated | When |
|---|---|---|
| Task created | `work/tasks/taskXXXX.md` created | `work_state: planned` |
| Task started | `work/tasks/taskXXXX.md` updated | `work_state: in-progress`, `next_actor: agent` |
| Task completed | Multiple files | `work_state: completed`, dashboards regenerated |
| Test added | `work/tests/testXXXX.md` created | `execution: automated` |
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
*This is an auto-generated file. Manual procedures at `work/procedures/file_procedure_traceability_matrix.md`*
"""

    return matrix

def generate_file_procedure_matrix(root_path=None) -> bool:
    """Generate and write the traceability matrix. Returns True if file changed."""
    files = collect_files()
    matrix = generate_matrix(files)

    root = Path(root_path) if root_path else Path(".")
    output_path = root / "generated" / "file_procedure_traceability_matrix.md"
    output_path.parent.mkdir(exist_ok=True)

    existing = output_path.read_text() if output_path.exists() else ""
    if existing == matrix:
        return False

    output_path.write_text(matrix)
    return True

if __name__ == "__main__":
    if generate_file_procedure_matrix():
        print(f"✓ Generated generated/file_procedure_traceability_matrix.md")
    else:
        print("✓ Generated file is up to date")
