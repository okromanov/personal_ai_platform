---
id: file_procedure_traceability_matrix
type: procedure_reference
title: File and Procedure Traceability Matrix
version: 1.5
created: 2026-08-23
updated: 2026-08-23
scope: project_state_management
purpose: Prevent state inconsistencies by documenting all file dependencies in state transitions
---

# File and Procedure Traceability Matrix

> This matrix documents all files that must be updated during each major state transition in the project.
> It serves as a checklist to ensure no files are left in inconsistent states during milestone acceptance, task state changes, and other critical procedures.

## 1. Milestone Acceptance (Example: m01 → completed)

### 1.1 Preconditions

- All tasks in milestone marked `completed`
- Semantic review completed
- All tests passing
- Owner approval issued

### 1.2 Files to Update (In Order)

| File | Field/Section | Old Value | New Value | Who | Validation |
|------|---|---|---|---|---|
| `work/m0X/semantic_review.md` | `review_state` | `pending` | `completed` | Agent | Must be `completed` to open acceptance |
| `work/m0X/semantic_review.md` | `updated` | previous date | current date | Agent | Must reflect actual modification |
| `work/m0X/semantic_review.md` | `reviewed_sha` | `null` | commit SHA | Agent | Must be SHA of acceptance commit |
| `work/m0X/semantic_review.md` | `reviewer` | `null` | `owner` | Agent | Must identify reviewer |
| `work/m0X/owner_checklist.md` | `acceptance_state` | `pending` | `accepted` | Owner | Owner decision checkpoint |
| `work/m0X/final_report.md` | `completion_state` | `in-progress` | `completed` | Agent | Summary of milestone work |
| `operations/quality_registry.json` | m0X profile | remove if `planned` | keep if active | Agent | Only active milestones have profiles |
| [`project_status.md`](../../project_status.md) | `current_milestone` | previous | next | Auto-generate | Dashboard must show next stage |
| [`project_status.md`](../../project_status.md) | `next_actor` | `owner` or `agent` | next recipient | Auto-generate | Must reflect workflow state |
| [`tasks.md`](../../tasks.md) | all milestone tasks | state varies | finalized state | Auto-generate | Task registry updated |
| [`generated/traceability_matrix.md`](../../generated/traceability_matrix.md) | milestone links | previous | updated | Auto-generate | Derived doc reflects new state |
| [`generated/document_index.md`](../../generated/document_index.md) | milestone entries | previous | updated | Auto-generate | Derived doc reflects new state |

### 1.3 Update Sequence

```
Semantic Review Manual Update
  ↓
Quality Registry Conditional Update (if planned → active)
  ↓
Final Report Update
  ↓
Auto-Generate: generate_project_status.py + generate_documents.py
  ↓
CI Validation: check generated drift + acceptance gate
```

### 1.4 Critical Constraints

1. **Semantic review** must complete BEFORE transition executes
2. **Quality registry** profile MUST be removed if milestone is staying in `planned` state
3. **Dashboard** auto-generation must run AFTER manual updates (not before)
4. **All date fields** must be synchronized to actual update date
5. **No file** can be left with mismatched `updated` field

### 1.5 Validation Rules

- `operations/scripts/documents/check.py --all` must pass
- `operations/scripts/quality/registry.py` validates profile state matches milestone state
- CI check `Check generated drift` ensures project_status.md, tasks.md, generated/* are consistent
- All `review_state: completed` files must have `reviewed_sha` and `reviewer` populated

---

## 2. Task State Transition (Example: planned → in-progress)

### 2.1 Preconditions

- Dependency task marked `completed`
- Agent ready to begin work
- Requirement specifications reviewed

### 2.2 Files to Update (In Order)

| File | Field/Section | Old Value | New Value | Who | Validation |
|------|---|---|---|---|---|
| `work/tasks/taskXXX_*.md` | `work_state` | `planned` | `in-progress` | Agent | Signals active work |
| `work/tasks/taskXXX_*.md` | `updated` | previous date | current date | Agent | Must reflect actual modification |
| `work/tasks/taskXXX_*.md` | `next_actor` | previous | `agent` | Agent | Clarifies who acts next |
| `work/tasks/taskXXX_*.md` | `allowed_paths` | narrow/empty | actual paths | Agent | MUST expand before coding |
| `work/tasks/taskXXX_*.md` | Section 5 Plan | checkbox states | mark start | Agent | Progress tracking |
| [`project_status.md`](../../project_status.md) | `current_project_task` | previous | new task | Auto-generate | Dashboard shows current task |
| [`project_status.md`](../../project_status.md) | `next_actor` | previous | `agent` | Auto-generate | Workflow state |
| [`project_status.md`](../../project_status.md) | Step list | previous | current steps | Auto-generate | What's happening now |
| [`tasks.md`](../../tasks.md) | task row | state varies | `in-progress` | Auto-generate | Task registry updated |
| [`generated/document_index.md`](../../generated/document_index.md) | task entries | previous | updated | Auto-generate | Derived doc reflects state |

### 2.3 Update Sequence

```
Task File Manual Update (work_state, allowed_paths)
  ↓
Auto-Generate: generate_project_status.py
  ↓
CI Validation: check generated drift
```

### 2.4 Critical Constraints

1. **Agent MUST expand `allowed_paths`** before any code changes (not after)
2. **Task `updated` field** must be TODAY's date, not an old date from specification
3. **Dashboard regeneration** MUST run after task file update
4. **No allowed_paths** can be left as just the task file itself (except initially)
5. **Section 5 Plan** checkboxes must start unchecked, checked only during execution

### 2.5 Validation Rules

- `operations/scripts/tasks/check_change_scope.py` verifies all changed files fit in `allowed_paths`
- `operations/scripts/documents/check.py` validates task file format and required fields
- CI check `Check generated drift` ensures project_status.md and tasks.md stay synchronized
- Test that `allowed_paths` is populated (not empty or single file only) before PR merge

---

## 3. Task Completion (completed → next task transition)

### 3.1 Preconditions

- All implementation work finished
- All tests passing
- Code review approved
- Changes merged to main

### 3.2 Files to Update (In Order)

| File | Field/Section | Old Value | New Value | Who | Validation |
|------|---|---|---|---|---|
| `work/tasks/taskXXX_*.md` | `work_state` | `in-progress` | `completed` | Agent | Signals completion |
| `work/tasks/taskXXX_*.md` | `updated` | previous date | current date | Agent | Must reflect actual completion |
| `work/tasks/taskXXX_*.md` | Section 8 Checklist | incomplete | all ✅ | Agent | All criteria met |
| `work/tests/test_XXX.md` (linked) | `execution` | `spec` or `planned` | `automated` | Agent | Evidence of testing |
| `work/tests/test_XXX.md` (linked) | `automated_evidence` | `null` | evidence source | Agent | Links to proof |
| `work/tests/test_XXX.md` (linked) | `updated` | previous date | current date | Agent | Reflects evidence generation |
| [`project_status.md`](../../project_status.md) | current task row | ✗ unchecked | ✅ checked | Auto-generate | Dashboard reflects completion |
| [`project_status.md`](../../project_status.md) | `next_actor` | `agent` (current) | `owner` or `agent` (next) | Auto-generate | Next workflow step |
| [`project_status.md`](../../project_status.md) | `current_project_task` | completed task | next task | Auto-generate | Shows new current task |
| [`tasks.md`](../../tasks.md) | completed task row | `in-progress` | `completed` | Auto-generate | Registry reflects state |
| [`generated/traceability_matrix.md`](../../generated/traceability_matrix.md) | task links | previous | updated | Auto-generate | Derived doc updated |

### 3.3 Update Sequence

```
Task Completion Manual Update (work_state, Section 8 checkmarks)
  ↓
Test Link Update (link TASK to TEST with evidence)
  ↓
Auto-Generate: generate_project_status.py + generate_documents.py
  ↓
CI Validation: all tests pass + generated drift check
```

### 3.4 Critical Constraints

1. **Task `work_state`** must be `completed` on the merged commit
2. **Test file** must be linked in task's `tests:` field
3. **Test evidence** must include actual proof (not just placeholder text)
4. **Test `updated` date** must match when evidence was actually generated
5. **All Section 8 checkmarks** must be ✅ before marking task complete
6. **Dashboard update** must run AFTER test linking (not before)

### 3.5 Validation Rules

- `operations/scripts/documents/check.py --all` verifies task→test linkage
- Tests linked in task file must exist and have matching `traces_to`
- Test evidence must reference actual test runs (not speculation)
- CI must pass with all component and test files in place
- No task can be marked `completed` without at least one `TEST` linked

---

## 4. New Test Specification Creation

### 4.1 Preconditions

- Task exists and defined
- Component specification finalized
- Test requirements identified

### 4.2 Files to Create/Update

| File | Action | Contents | Who | Validation |
|------|---|---|---|---|
| `work/tests/test_XXX.md` | Create | Full test spec | Agent | Must match schema |
| `work/tasks/taskYYY_*.md` | Update | Add `tests: [TEST_XXX]` | Agent | Links task to test |
| [`generated/document_index.md`](../../generated/document_index.md) | Auto-generate | Add test entry | Script | Reflects new test |
| [`generated/traceability_matrix.md`](../../generated/traceability_matrix.md) | Auto-generate | Add test traces | Script | Shows all linkages |

### 4.3 Test Specification Requirements

For **automated tests**:
- `execution: automated`
- `automated_evidence: quality_suite` or similar
- Include sections: Purpose, What's checked, Automatic execution, Success criteria, Evidence, Owner actions (with "Действия владельца не требуются")
- NO `## 3. Действия владельца` section header (causes CI failure)
- `updated` field MUST match actual creation/modification date
- `spec_state: current` (not `planned`)
- `depends_on` lists any prerequisite tests

### 4.4 Validation Rules

- Test file must have schema matching document specification rules for semantic review
- Test name must match `TEST_XXX` pattern (T-E-S-T underscore three digits)
- Metadata consistency check: all dates must be ISO format
- Traceability check: test must appear in at least one task's `tests:` field

---

## 5. Component Implementation (architecture → code → test → evidence)

### 5.1 Files Affected During Implementation

```
ARC_CMP_XXX specification defined
  ↓
TASK_XXX created → work/tasks/taskXXX_*.md
  ↓
allowed_paths expanded in TASK
  ↓
Implementation in src/... (within allowed_paths)
  ↓
TEST_YYY created → work/tests/test_YYY.md
  ↓
Evidence generated (test runs, logs, artifacts)
  ↓
TASK linked to TEST
  ↓
project_status.md regenerated
  ↓
tasks.md regenerated
  ↓
generated/* regenerated
```

### 5.2 Critical Ordering

1. **Specification first** - ARC_CMP defined before TASK created
2. **Task before code** - allowed_paths must exist before changes
3. **Code then test** - implementation must be complete before evidence
4. **Test then link** - TEST file must exist before TASK references it
5. **Dashboard last** - auto-generate runs AFTER all manual updates

---

## 6. Procedure Dependencies and Automatic Triggers

### 6.1 Scripts That Auto-Update Files

| Script | Location | Triggered By | Updates | Side Effects |
|---|---|---|---|---|
| `generate_project_status.py` | `operations/scripts/status/` | Manual or CI | [`project_status.md`](../../project_status.md) | Reads all task/milestone files |
| `generate.py` (documents) | `operations/scripts/documents/` | CI always, manual optional | `generated/*` [`tasks.md`](../../tasks.md) | Regenerates all derived docs |
| `full_traceability.py` | `operations/scripts/traceability/` | Called by generate.py | [`generated/traceability_matrix.md`](../../generated/traceability_matrix.md) | Links TASK→TEST→REQUIREMENT |
| `semantic_consistency.py` | `operations/scripts/traceability/` | Validation, CI | Validates only | No file updates |
| `generate.py` task mode | `operations/scripts/documents/` | Manual when creating tasks | `work/tasks/*.md` | Auto-creates task files |

### 6.2 Manual Update Points (Must NOT Be Skipped)

| Update | File | Field | Frequency | Consequence if Skipped |
|---|---|---|---|---|
| Semantic review completion | `semantic_review.md` | `review_state` → `completed` | Per milestone | Acceptance gate blocked |
| Task state advance | `task_*.md` | `work_state` | Per task transition | Dashboard shows old state |
| Allowed paths expansion | `task_*.md` | `allowed_paths` | At task start | Scope validation fails |
| Test linkage | `task_*.md` | `tests:` field | Per completed task | Traceability broken |
| Test evidence | `test_*.md` | Evidence section | Per test run | Acceptance blocked (no proof) |

### 6.3 File Validation Checkpoints

```
Pre-commit:
  - Document metadata consistency (dates, formats, required fields)
  - File links validity (all references exist)

During CI (Windows validation):
  - Regenerate derived documents
  - Check generated drift (project_status.md, tasks.md, generated/*)
  - Document checker validates all files against schema
  - Unit tests pass

During CI (Quality skills):
  - Full quality suite with coverage
  - Metadata consistency across commits
  - Registry validation (profiles only for active milestones)
```

---

## 7. High-Risk File Inconsistencies (History of Issues)

### 7.1 Semantic Review Not Updated After Acceptance

**Issue**: [`work/m01/semantic_review.md`](../m01/semantic_review.md) left with `review_state: pending` after m01 was accepted.

**Root Cause**: Acceptance procedure didn't include explicit step to update semantic_review.md file.

**Prevention**: 
- Add semantic_review.md to mandatory update list for milestone acceptance
- Validate that completed milestone files have `review_state: completed`
- Document that review completion is NOT automatic—must be manual step

**Recovery**:
```
1. Manually set review_state: completed
2. Set reviewed_sha to acceptance commit SHA
3. Set reviewer field
4. Update timestamp to current date
5. Commit and push
```

### 7.2 Dashboard Not Updating After Task Completion

**Issue**: Dashboard still showed TASK_001 as current after it was marked completed.

**Root Cause**: Auto-generation script wasn't explicitly called or wasn't detecting state changes.

**Prevention**:
- CI workflow MUST run `generate_project_status.py` on every main branch push
- Dashboard generation should not rely on conditional execution
- Verify generated drift check catches any dashboard inconsistencies

**Recovery**:
```
python3 operations/scripts/status/generate_project_status.py
git diff project_status.md  # Review changes
git add project_status.md
git commit -m "Regenerate project status after task state update"
```

### 7.3 Test File `updated` Field Mismatched with Actual Modification Date

**Issue**: `test_0008.md` (a since-removed stub, see §7.5) claimed `updated: 2026-08-22` but was actually modified 2026-08-23.

**Root Cause**: Template or batch creation set dates without verifying actual modification times.

**Prevention**:
- Check script validates that `updated` date ≤ current date
- On file modification, update the `updated` field to TODAY (required)
- Pre-commit hook can auto-fix if allowed

**Recovery**:
```
1. Update metadata `updated` field to current date
2. Re-run document checker
3. Commit with message mentioning date correction
```

### 7.4 Quality Registry Profile for Planned Milestone

**Issue**: `quality_registry.json` contained profile for m02 while it was in `planned` state.

**Root Cause**: Profile was created prematurely; should only exist for ACTIVE milestones.

**Prevention**:
- Test `test_repository_registry_defines_only_current_quality_horizon` validates this
- Quality registry MUST only have profiles for milestones with `state: in-progress` or `completed`
- Profiles MUST be removed when milestone transitions back to `planned`

**Recovery**:
```
1. Remove entire milestone profile block from quality_registry.json
2. Verify remaining profiles are only for active milestones
3. Re-run quality registry validation
```

### 7.5 TEST Stubs Created to Satisfy the Linkage Checker Instead of Real Verification

**Issue**: `test_0008.md`–`test_0019.md` were created as placeholder specs for
ARC_CMP_002–009 and INF_CMP_001–008, declaring `execution: automated` and
`automated_evidence: quality_suite` while the components themselves did not
exist yet (`Доказательство реализации будет представлено при выполнении
TASK_000X`). `quality_suite` evidence trivially "passes" for a component with
no code and no test exercising it, so this made the traceability matrix claim
verification that never happened.

**Root Cause**: TEST documents were generated in bulk to make a linkage/scope
checker pass, rather than written when a requirement was actually implemented
and had real evidence — the opposite of the rule this document itself states
in `generate.py`: TEST specs are not auto-generated because they require a
real evidence source that only exists once the requirement is implemented.

**Prevention**:
- AGENTS.md §5.1 explicitly forbids stub TEST/TASK docs claiming automated
  evidence that does not exist.
- Removing the 12 stub files did not break `test_specs`, `full_traceability`,
  or `acceptance_model` — confirming no check actually required them; they
  were unnecessary defensive padding, not a real constraint.

**Recovery**:
```
1. Delete the stub TEST file (git rm work/tests/test_00XX.md)
2. Confirm the owning TASK does not reference it in `tests:` (none did here)
3. Regenerate derived docs: python3 operations/scripts/documents/generate.py --all
4. Write the real TEST spec only when the component is actually implemented
```

---

## 8. Implementation Checklist for State Transitions

### When Accepting a Milestone

- [ ] Semantic review file updated (review_state, updated, reviewed_sha, reviewer)
- [ ] Owner checklist marked accepted
- [ ] Quality registry profile removed if staying planned (or updated if becoming active)
- [ ] Final report file created/updated
- [ ] All task files have updated dates matching TODAY
- [ ] All test files have updated dates matching TODAY
- [ ] Run: `python3 operations/scripts/status/generate_project_status.py`
- [ ] Run: `python3 operations/scripts/documents/generate.py --all`
- [ ] Verify: `git diff project_status.md tasks.md generated/` shows expected changes
- [ ] Verify: `operations/scripts/documents/check.py --all` passes
- [ ] CI passes: Windows validation + Quality skills

### When Starting a Task

- [ ] TASK file: set `work_state: in-progress`
- [ ] TASK file: expand `allowed_paths` with actual implementation paths
- [ ] TASK file: set `updated: today`
- [ ] TASK file: set `next_actor: agent`
- [ ] Run: `python3 operations/scripts/status/generate_project_status.py`
- [ ] Verify: Dashboard shows new task as current
- [ ] Commit with message including task number

### When Completing a Task

- [ ] TASK file: set `work_state: completed`
- [ ] TASK file: mark all Section 8 checkboxes ✅
- [ ] TEST file: set `execution: automated`, `automated_evidence: quality_suite`
- [ ] TEST file: add evidence section with actual test results
- [ ] TASK file: add `tests: [TEST_XXX]` if not already there
- [ ] All files: verify `updated: today`
- [ ] Run: `python3 operations/scripts/status/generate_project_status.py`
- [ ] Run: `python3 operations/scripts/documents/generate.py --all`
- [ ] CI must pass
- [ ] Merge to main
- [ ] Verify dashboard now shows next task

---

## 9. File State Validation Script (Recommended Enhancement)

To automate consistency checks, recommend adding:

```python
# operations/scripts/validation/state_consistency_check.py

def validate_milestone_acceptance_state(milestone_name):
    """Ensure all files related to accepted milestone are consistent."""
    checks = [
        semantic_review_completed(),
        owner_checklist_accepted(),
        quality_profile_correct_state(),
        all_tasks_properly_transitioned(),
        all_test_files_have_evidence(),
        dashboard_shows_next_milestone(),
        generated_docs_current(),
    ]
    return all(checks)

def validate_task_state(task_id):
    """Ensure task and related files are consistent."""
    checks = [
        task_file_has_allowed_paths(),
        allowed_paths_not_empty(),
        test_file_exists_if_task_complete(),
        test_linked_in_task_file(),
        task_state_in_dashboard(),
    ]
    return all(checks)

def validate_file_timestamps():
    """Ensure all 'updated' fields match modification dates."""
    files = all_specification_files()
    for f in files:
        metadata_date = read_yaml_field(f, 'updated')
        modification_date = git_last_modify_date(f)
        assert metadata_date >= modification_date, \
            f"{f}: metadata date {metadata_date} < modification {modification_date}"
```

---

## 10. References

- **Semantic Review Procedure**: [`work/m01/semantic_review.md`](../m01/semantic_review.md)
- **Quality Registry Rules**: `operations/quality_registry.json`
- **Document Schema**: See operations/semantic_review.md specification
- **Acceptance Model**: `operations/scripts/acceptance/apply.py`
- **Project Status Generation**: `operations/scripts/status/generate_project_status.py`
- **Document Generation**: `operations/scripts/documents/generate.py`
- **Validation Scripts**: `operations/scripts/documents/check.py`

---

**Last Updated**: 2026-08-23  
**Scope**: All v1 milestones (m01–m06)  
**Owner**: Project automation team  
**Review Cycle**: Per major procedure change, minimum quarterly

