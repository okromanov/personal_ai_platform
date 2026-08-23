<!-- generated file: do not edit manually -->
---
id: file_procedure_traceability_matrix_generated
type: generated_traceability_matrix
generation_state: generated
version: 1.0
created: 2026-08-23
updated: 2026-08-23
---

# File and Procedure Traceability Matrix (Auto-generated)

> Automatic matrix of file state transitions and their dependencies.
> Regenerated on each CI run from actual project structure.
> Manual matrix kept at: See `work/procedures/` for detailed procedures documentation

## Task → Test → Component Linkage

| Task | State | Test | Test Status | Component |
|---|---|---|---|---|

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
- `work/m0X/final_report.md` - completion report (regenerated after acceptance
  by `operations/scripts/milestones/update_completion_report.py`)

owner_checklist.md and semantic_review.md are not auto-created: they are
written by hand only when a milestone needs a record beyond what
operations/acceptance.md and operations/semantic_review.md already specify.

---

*Last generated: 2026-08-23*
*This is an auto-generated file.*
