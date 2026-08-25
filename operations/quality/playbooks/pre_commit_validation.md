---
id: pre_commit_validation
type: guide
document_state: current
version: 1.0
updated: 2026-08-25
---

# Pre-Commit Validation

**ID:** pre_commit_validation  
**Type:** Blocking Quality Gate  
**Frequency:** Every local commit, every push, every pull request  
**Framework:** LLM-agnostic

## Purpose

Run the canonical fast gate before a commit leaves the developer's machine. The hook and GitHub Actions delegate to the same Python runner with different `fast` and `full` profiles.

## Install

```bash
python3.12 -m pip install -r operations/quality/requirements_dev.txt
cp operations/hooks/pre_commit_hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Checks

The hook first checks staged authority-document version bumps and required development tools. It then invokes `run_suite.py fast`, which blocks Python/JSON/TOML errors, unpinned or duplicate development requirements, fast repository-check findings, Ruff lint, unit-test failures, generated drift, and executable Python files.

The full server profile adds Ruff formatting, mypy regression, aggregate/per-module/diff coverage and evidence artifacts. Actionlint, ShellCheck, pip-audit and Gitleaks run as independent server gates.

## Run

```bash
bash operations/hooks/pre_commit_hook.sh
```

## Success Criteria

- Exit code `0` from the canonical hook.
- No check is silently skipped because a required development dependency is missing.
- Generated files are identical to the staged source state.

## Failure Actions

Fix the reported issue, stage the corrected files, and run the hook again. `git commit --no-verify` is not an ordinary recovery path; any emergency bypass must be explicitly reviewed and followed by the full server gate.
