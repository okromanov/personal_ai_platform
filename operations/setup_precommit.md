---
id: setup_precommit
type: guide
document_state: current
applicability: normative
version: 1.6
updated: 2026-09-26
depends_on:
  - operations_change_process
  - coding_agent_instruction
---

# Git Hook Setup

## Overview

The repository includes two canonical Git hooks in `operations/hooks/`:

- `pre_commit_hook.sh` — runs the `fast` quality profile before each commit.
- `pre_push_hook.sh` — runs the `full` quality profile before each push.

Both hooks are bash scripts. On Windows execute them with **Git Bash** (shipped
with [Git for Windows](https://git-scm.com/download/win)), not with the WSL
launcher stub `C:\Windows\System32\bash.exe`.

## Installation

### Automatic Installation

Run the following commands in the repository root with Git Bash:

```bash
cp operations/hooks/pre_commit_hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
cp operations/hooks/pre_push_hook.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
```

### Manual Verification

Verify the hooks are installed and executable:

```bash
ls -la .git/hooks/pre-commit .git/hooks/pre-push
```

## What the Pre-commit Hook Checks

The pre-commit hook runs five top-level steps:

1. **Auto-fix cross-references** — links cross-references in staged Markdown
   files and re-stages them.
2. **Authority document version bumps** — validates that authority documents
   with semantic changes bump their versions. Authority documents include:
   - [project_rules.md](../project_rules.md)
   - [AGENTS.md](../AGENTS.md)
   - [operations/change_process.md](../operations/change_process.md)
   - [specifications/business_requirements.md](../specifications/business_requirements.md)
   - [specifications/threat_model.md](../specifications/threat_model.md)
   - [specifications/system_specification.md](../specifications/system_specification.md)
   - [specifications/architecture_baseline.md](../specifications/architecture_baseline.md)
   - [specifications/infrastructure_baseline.md](../specifications/infrastructure_baseline.md)
3. **Development tools** — fails when pinned development tools are not
   installed.
4. **Canonical fast quality suite** — Python syntax and JSON validity, fast
   documentation/governance checks, Ruff lint, all unit tests, deterministic
   generation and drift, executable-bit rejection for Python source files.
5. **Dashboard regeneration** — runs after the suite passes
   (`operations/hooks/pre_commit_regenerate_dashboards.sh`) and fails closed.
   Validates [`operations/template_registry.json`](template_registry.json)
   before regeneration. Triggers on any staged Markdown file, bumps only
   documents whose staged version still equals the version in `HEAD`, then
   regenerates [`project_status.md`](../project_status.md) from its registered
   template and re-stages it if changed. TASK cards, acceptance reports, audit
   history and runtime reports are created only by their separate explicit
   commands; the dashboard hook has no such side effects.

The server `full` profile (run by the pre-push hook and CI) adds formatting,
mypy, aggregate/per-module/diff coverage and security tooling.

## What the Pre-push Hook Checks

The pre-push hook runs the canonical `full` quality profile. It is an optional
local safety net; the mandatory checks remain pre-commit, the full local gate,
and the server-side Project check.

## Python Version Requirements

The hooks require Python 3.12 or newer and will automatically detect:

1. Python 3.14, 3.13, or 3.12 (in that order)
2. Generic `python3` command, but only when it resolves to Python 3.12+
3. Generic `python` command, but only when it resolves to Python 3.12+

If none are found, the hook fails with an error.

## Troubleshooting

### Hook fails with "No Python 3.12+ found"

Ensure Python 3.12+ is installed and available in your PATH:

```bash
python3.12 --version
```

### Hook fails on documentation check

Run the documentation check manually to see detailed errors:

```bash
python3.12 operations/scripts/documents/check.py --fast
```

For full validation:

```bash
python3.12 operations/scripts/documents/check.py --all
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

**Warning:** This should only be used for emergency fixes. The hook validates
important constraints.

## Development Workflow

1. Make your changes
2. Stage files with `git add`
3. Attempt to commit with `git commit`
4. If the hook fails:
   - Fix the issues
   - Stage the corrected files
   - Commit again
5. Push to the repository
