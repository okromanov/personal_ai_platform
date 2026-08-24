# Unit Tests and Coverage Check

**ID:** unit_tests  
**Type:** Blocking Quality Gate  
**Frequency:** Every push, every pull request, or on-demand  
**Framework:** LLM-agnostic

## Purpose

Run the complete unittest suite and prevent measured coverage of `operations/scripts` from falling below the checked-in floor.

## Run

```bash
python3.12 -m pip install -r operations/quality/requirements_dev.txt
python3.12 operations/scripts/quality/run_suite.py full
```

Coverage configuration lives in `pyproject.toml`. The policy requires at least 85% aggregate branch coverage, at least 85% for listed critical modules, and at least 90% line coverage for changed executable Python lines when a Git base is supplied.

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

## Test Categories Under Discovery

`operations/tests/` is discovered as one flat unittest tree — there is no
separate command or profile per category. The categories below live inside
that discovery and share its pass/fail gate:

| Category | Path | Focus |
|---|---|---|
| Core logic | `operations/tests/test_*.py` | Acceptance, governance, lifecycle, generation |
| Tooling | `operations/tests/tooling/` | Quality scripts, registries, traceability |
| Boundary cases | `test_boundary_cases.py` | Empty/whitespace/Unicode/malformed input to parsing and confirmation functions |
| Concurrency | `test_concurrency.py` | Real-thread races against `atomic_write` (torn writes, torn reads) |
| Security (extended) | `test_security_extended.py` | Subprocess injection resistance, provenance spoofing, path-traversal containment — beyond the document/workflow governance already covered in `test_governance_hardening.py` |
| Durability | `test_durability.py` | `atomic_write` crash-mid-write and content-integrity guarantees |
| Performance | `performance/test_critical_paths.py` | Wall-clock ceilings on `atomic_write`, `read_text`, and path validation to catch algorithmic (e.g. O(n²)) regressions |
| Stress/scalability | `stress/test_scalability.py` | Milestone/task parsing and directory traversal at 10–100x today's repository size |
| Integration | `integration/` | End-to-end checks that the quality tools themselves run correctly together (see [integration_tests](integration_tests.md)) |

Performance and stress tests assert generous ceilings and correctness at
scale, not tight SLAs — they exist to catch a regression that turns a 1s
check into a multi-minute CI hang, not to enforce a benchmark target.
