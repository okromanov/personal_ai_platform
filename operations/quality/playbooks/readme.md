---
id: quality_playbooks_readme
type: guide
document_state: current
version: 1.0
updated: 2026-08-25
---

# Repository Quality Playbooks

The files in this directory are repository-specific QA playbooks. Their commands are framework-agnostic and can be followed by Claude, Codex, another agent, or a human. They are not standalone portable Agent Skill packages: the enforceable source of truth is the checked-in scripts, configuration, and GitHub Actions workflow. Playbooks do not reimplement the canonical suite.

## Setup

```bash
python3.12 -m pip install -r operations/quality/requirements_dev.txt
cp operations/hooks/pre_commit_hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Optional but recommended: catch mypy/format/coverage/security/dead-code
# regressions before they leave the machine, not just on the next CI run.
cp operations/hooks/pre_push_hook.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Playbooks

| Playbook | Blocking behavior | Canonical command |
|---|---|---|
| [security_audit](security_audit.md) | Zero HIGH severity security issues | `python3.12 -m bandit -r operations/scripts --severity-level medium` |
| [dead_code_audit](dead_code_audit.md) | Zero unused functions; duplication < 5% | `python3.12 -m vulture operations/scripts --min-confidence 80` |
| [code_quality_check](code_quality_check.md) | Manual findings classified by severity | `python3.12 operations/scripts/quality/code_analyzer.py` |
| [documentation_audit](documentation_audit.md) | Zero checker errors and warnings | `python3.12 operations/scripts/documents/check.py --all` |
| [pre_commit_validation](pre_commit_validation.md) | Fast syntax, JSON/TOML/dependency, repository, Ruff, unit-test and drift checks | `bash operations/hooks/pre_commit_hook.sh` |
| [pre_push_validation](pre_push_validation.md) | Full local profile (mypy, format, coverage, security, dead-code) before code leaves the machine | `bash operations/hooks/pre_push_hook.sh` |
| [python_lint_check](python_lint_check.md) | Zero findings for the configured Ruff rules and format | `python3.12 -m ruff check ...` |
| [python_type_check](python_type_check.md) | No total or per-file/error-code increase over checked-in mypy debt | `python3.12 operations/scripts/quality/run_mypy_baseline.py` |
| [unit_tests](unit_tests.md) | All tests pass and coverage stays above its floor | Follow the coverage commands in the playbook |
| [integration_tests](integration_tests.md) | End-to-end quality pipeline works; no component interactions broken | `python3.12 -m unittest discover -s operations/tests/integration` |

## Full Local Suite

```bash
python3.12 operations/scripts/quality/run_suite.py full
bash operations/hooks/pre_commit_hook.sh
```

## Event Integration

`.github/workflows/project_check.yml` runs validation:

- on every push to any branch;
- on every pull request;
- for every merge-queue candidate;
- on manual dispatch.

There is no scheduled (cron) run: every code change already triggers the full
suite via push or pull_request, so a time-based run would only re-check an
unchanged tree.

The final `Project check` gate requires Windows portability validation and the canonical Linux quality suite. The Linux job also runs Actionlint, ShellCheck, pip-audit and Gitleaks. Failed jobs upload diagnostic artifacts when available.

## Honest Baselines

- Dynamic test and checker counts come from the current run, not this document.
- The canonical unittest runner fails on every skipped test; an unavailable prerequisite is a gate failure, not a silent pass.
- Aggregate, critical-module and changed-line coverage floors live in `pyproject.toml`; the mypy debt budget lives in [`operations/quality_baseline.json`](../../quality_baseline.json).
- A passing mypy baseline means no regression; it does not mean zero type errors until the budget reaches zero.
- Ruff and development-tool versions are pinned in [`operations/quality/requirements_dev.txt`](../requirements_dev.txt).
- Quality claims are bound to a Git SHA and CI run; an older green run is not evidence for a newer revision.

## Improving the Baseline

When a change fixes type errors or increases sustainable coverage, lower the error budget or raise the coverage floor in the same reviewed change. Never relax a baseline merely to make CI green.

**Updated:** 2026-08-23  
**Version:** 3.4
