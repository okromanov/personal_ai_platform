---
id: integration_tests
type: guide
document_state: current
version: 1.0
updated: 2026-08-25
---

# Integration Tests Playbook

**ID:** integration_tests  
**Type:** Blocking Quality Gate  
**Frequency:** Every push, every pull request, or on-demand  
**Framework:** unittest-based

## Purpose

Run integration tests that verify multiple components work together correctly. These tests check end-to-end functionality of quality tools, acceptance flows, and critical workflows.

## Scope

Tests located in `operations/tests/integration/`:
- Quality pipeline integration
- Acceptance workflow integration
- Status generation integration
- Documentation generation integration

## Run

```bash
python3.12 -m pip install -r operations/quality/requirements_dev.txt
python3.12 -m unittest discover -s operations/tests/integration -p "test_*.py" -v
```

## Categories

### Quality Pipeline Integration

**File:** `test_quality_pipeline.py`

Verifies:
- Code analyzer produces valid JSON output
- Ruff linter integration with project config
- Bandit SAST scanner runs correctly
- Vulture dead code detection works
- Mypy type checking processes baseline correctly

**Success Criteria:**
- All tools run without crashing
- All tools produce valid output format
- Exit codes indicate correct pass/fail state

### Acceptance Workflow Integration

**Tests:** Transitions between states, CLI interactions, database updates

**Success Criteria:**
- State transitions are atomic or properly rolled back
- CLI commands produce expected output
- Database state is consistent after operations

### Documentation Generation Integration

**Tests:** Check generation, traceability matrix, index creation

**Success Criteria:**
- Generated files are bit-identical with expected output
- Cross-references are validated
- No orphaned document references

## Success Criteria (All)

- ✅ All integration tests pass
- ✅ No skipped tests (unavailable prerequisites cause failure)
- ✅ No resource leaks (temp files cleaned up)
- ✅ Tests are independent (can run in any order)
- ✅ Coverage increases or stays the same

## Difference from Unit Tests

| Aspect | Unit Tests | Integration Tests |
|--------|-----------|-------------------|
| Focus | Individual functions | Component interactions |
| Scope | Single module | Multiple modules |
| Setup | Mocks and stubs | Real dependencies |
| Speed | Fast (< 1s each) | Slower (1-10s each) |
| Isolation | Complete | Partial (may share state) |

## Failure Actions

1. **Identify which components failed to interact**
2. **Check order dependency** - Does test pass when run alone?
3. **Verify state cleanup** - Is state from previous test bleeding?
4. **Fix the component** or add proper setup/teardown
5. **Add assertion to catch future regressions**

## Configuration

Integration tests can access real project files but should:
- Use a `runtime/` subdirectory for temporary output
- Not modify source files
- Clean up after themselves
- Have explicit setup/teardown

## When to Run

- **Automatic:** Every push and PR (after unit tests pass)
- **Manual:** When components change (acceptance, status, documents)
- **Before release:** Verify all workflows work end-to-end

## Related Skills

- [unit_tests](unit_tests.md) - Fast, isolated unit testing
- [pre_commit_validation](pre_commit_validation.md) - Pre-commit gate
- [code_quality_check](code_quality_check.md) - Code audit
