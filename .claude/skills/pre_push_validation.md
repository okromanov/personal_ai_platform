# Pre-Push Validation

**ID:** pre_push_validation  
**Type:** Blocking Quality Gate (opt-in, local)  
**Frequency:** Every local `git push`, once installed  
**Framework:** LLM-agnostic

## Purpose

Run the canonical **full** quality profile — the same one CI enforces — before a commit leaves the developer's machine, instead of finding out about a mypy, formatting, coverage, security, or dead-code regression only after pushing. `pre_commit_validation` intentionally only runs the fast profile on every commit to keep commits quick; this hook closes that gap at the point code actually leaves the machine.

## Install

```bash
python3.12 -m pip install -r operations/quality/requirements_dev.txt
cp .claude/skills/pre_push_hook.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

`operations/hooks/pre_push_hook.sh` is only a compatibility wrapper that delegates to this canonical file. This hook is opt-in: nothing installs it automatically, and CI remains the enforced gate regardless of whether a developer has it installed locally.

## Checks

The hook invokes `run_suite.py full`, which runs (in order): derived-document regeneration, documentation audit, Bandit security scan, AST code-quality analysis, Vulture dead-code detection, Ruff lint, Ruff format check, mypy regression, unit tests under branch coverage, aggregate/critical-module coverage policy, and generated-file drift.

Changed-line diff coverage is skipped locally (no `--coverage-base` is passed, so the suite runs with `--skip-diff`) — that check only makes sense against a PR base and still runs in CI.

Actionlint, ShellCheck, pip-audit and Gitleaks stay CI-only: they fetch pinned external binaries over the network with SHA-256 verification, which is heavier machinery than a local git hook should depend on. A developer who touches `.github/workflows/`, shell scripts, or `requirements_dev.txt` should still expect CI to be the first place those specific checks run.

## Run

```bash
bash .claude/skills/pre_push_hook.sh
```

## Success Criteria

- Exit code `0` from the canonical hook.
- Same pass/fail outcome as the CI `quality-skills` job would report for the same tree (modulo diff coverage, which needs a PR base).

## Failure Actions

Fix the reported issue and push again. `git push --no-verify` is not an ordinary recovery path; any emergency bypass must be explicitly reviewed and followed by the full server gate, which cannot be bypassed.

## Related Skills

- [pre_commit_validation](pre_commit_validation.md) - Fast, mandatory-pattern local gate on every commit
- [unit_tests](unit_tests.md) - Test discovery and coverage policy this hook enforces
