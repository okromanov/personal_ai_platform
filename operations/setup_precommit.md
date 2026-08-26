---
id: setup_precommit
type: guide
document_state: current
version: 1.3
updated: 2026-08-25
depends_on:
  - operations_change_process
  - coding_agent_instruction
---

# Pre-commit Hook Setup

## Overview

The repository includes one canonical pre-commit hook in `operations/hooks/pre_commit_hook.sh`.

## Installation

### Automatic Installation

Run the following command in the repository root:

```bash
cp operations/hooks/pre_commit_hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

### Manual Verification

Verify the hook is installed:

```bash
ls -la .git/hooks/pre-commit
```

You should see an executable file.

## What the Hook Checks

The pre-commit hook runs three top-level steps. Its canonical `fast` runner performs the detailed technical checks.

### 1. Authority Document Version Bumps
- Validates that authority documents with semantic changes bump their versions
- Authority documents include:
  - [project_rules.md](../project_rules.md)
  - [AGENTS.md](../AGENTS.md)
  - [operations/change_process.md](../operations/change_process.md)
  - [specifications/business_requirements.md](../specifications/business_requirements.md)
  - [specifications/threat_model.md](../specifications/threat_model.md)
  - [specifications/system_specification.md](../specifications/system_specification.md)
  - [specifications/architecture_baseline.md](../specifications/architecture_baseline.md)
  - [specifications/infrastructure_baseline.md](../specifications/infrastructure_baseline.md)

### 2. Development Tools

- Fails when pinned development tools are not installed.

### 3. Canonical Fast Suite

- Python syntax and JSON validity;
- fast documentation/governance checks;
- Ruff lint;
- all unit tests;
- deterministic generation and drift;
- executable-bit rejection for Python source files.

The server `full` profile adds formatting, mypy, aggregate/per-module/diff coverage and security tooling.

### 4. Dashboard Regeneration

- Runs after the suite passes (`operations/hooks/pre_commit_regenerate_dashboards.sh`), non-blocking.
- Triggers on **any** staged `.md` file, not only `work/tasks|tests|mXX/` — every tracked document's frontmatter (`id`/`type`/`version`/state) feeds [`generated/markdown_index.md`](../generated/markdown_index.md), [`generated/repository_structure.md`](../generated/repository_structure.md), [`generated/traceability_matrix.md`](../generated/traceability_matrix.md) and [`generated/test_catalog.md`](../generated/test_catalog.md), so a version bump anywhere (e.g. an ADR or [AGENTS.md](../AGENTS.md)) drifts them the same way a TASK/TEST change does.
- Bumps versions of the staged `.md` files, regenerates [`project_status.md`](../project_status.md) and `generated/*`, then re-stages whatever changed.

## Python Version Requirements

The hook requires Python 3.12 or newer and will automatically detect:

1. Python 3.14, 3.13, or 3.12 (in that order)
2. Generic `python3` command
3. Generic `python` command

If none are found, the hook fails with an error.

## Troubleshooting

### Hook fails with "No Python 3.12+ found"

Ensure Python 3.12+ is installed and available in your PATH:

```bash
python3 --version
```

### Hook fails on documentation check

Run the documentation check manually to see detailed errors:

```bash
python3 operations/scripts/documents/check.py --fast
```

For full validation:

```bash
python3 operations/scripts/documents/check.py --all
```

### Hook fails on authority document versions

If you modified an authority document but didn't update its version field:

1. Check the current version:
   ```bash
   grep "^version:" <document-path>
   ```

2. Increment the version in the document's front matter

3. Stage the file and commit again

### Disabling the Hook Temporarily

To skip the hook for a specific commit:

```bash
git commit --no-verify
```

**Warning:** This should only be used for emergency fixes. The hook validates important constraints.

## Development Workflow

1. Make your changes
2. Stage files with `git add`
3. Attempt to commit with `git commit`
4. If the hook fails:
   - Fix the issues
   - Stage the corrected files
   - Commit again
5. Push to the repository

## Hook Performance

- Typical execution time: 0.5-1 second
- Fast documentation check: < 0.5 seconds
- Full documentation check: < 1.2 seconds

The pre-commit hook uses the fast documentation check mode to keep commit operations responsive.
