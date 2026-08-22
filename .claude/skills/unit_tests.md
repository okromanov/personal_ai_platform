# Unit Tests and Coverage Check

**ID:** unit_tests  
**Type:** Blocking Quality Gate  
**Frequency:** Every push, every pull request, weekly, or on-demand  
**Framework:** LLM-agnostic

## Purpose

Run the complete unittest suite and prevent measured coverage of `operations/scripts` from falling below the checked-in floor.

## Run

```bash
python3.12 -m pip install -r operations/quality/requirements_dev.txt
python3.12 operations/scripts/quality/run_suite.py full
```

Coverage configuration lives in `pyproject.toml`. The policy requires at least 75% aggregate branch coverage, at least 85% for listed critical modules, and at least 90% line coverage for changed executable Python lines when a Git base is supplied.

## Success Criteria

- All discovered tests pass with zero failures and errors.
- No test is silently skipped.
- Total coverage is at or above the configured floor.
- Every critical module and changed-line threshold passes.
- Generated test counts are read from the current run, never copied into a permanent report.

## Failure Actions

1. Fix the failed behavior or test expectation; never suppress a failing test.
2. Add behavioral tests when new logic lowers aggregate, module, or diff coverage.
3. Raise the floor when coverage increases sustainably.
4. Do not lower the floor without an explicit reviewed rationale.

## Output

Report the discovered test count, failures/errors/skips, duration, total coverage, lowest-covered critical modules, and the exact Git SHA when running in CI.
