---
id: python_type_check
type: guide
document_state: current
version: 1.0
updated: 2026-08-25
---

# Python Type Regression Check

**ID:** python_type_check  
**Type:** Incremental Quality Gate  
**Frequency:** Every push, every pull request, or on-demand  
**Framework:** LLM-agnostic

## Purpose

Run mypy across `operations/scripts/` and `operations/tests/` and prevent the known type debt from increasing. The repository is not yet fully typed, so this gate is explicitly incremental rather than claiming zero errors.

## Run

```bash
python3.12 -m pip install -r operations/quality/requirements_dev.txt
python3.12 operations/scripts/quality/run_mypy_baseline.py
```

The wrapper runs mypy, prints every finding, and compares both the total and each `file + error-code` bucket with [`operations/quality_baseline.json`](../../../operations/quality_baseline.json). This prevents a new category of error from being hidden by an unrelated fix elsewhere.

## Success Criteria

- The mypy error count does not exceed `mypy_error_budget`.
- No file/error-code bucket exceeds its checked-in limit and no new bucket appears.
- Any change that fixes type debt reduces the budget in the same change.
- An increase fails CI even when unit tests pass.
- When the count reaches zero, the budget is set to `0` and the wrapper becomes a zero-error gate.

## Failure Actions

1. Inspect new errors first.
2. Fix the new regression or improve annotations.
3. Do not raise the budget merely to make CI green.
4. Keep the pinned mypy version in [`operations/quality/requirements_dev.txt`](../../../operations/quality/requirements_dev.txt) synchronized with intentional baseline recalculation.

## Output

Report:

1. Current error count and allowed budget.
2. File/error-code buckets that changed relative to the baseline.
3. Files with the highest remaining debt.
4. The next small group of annotations worth fixing.

## Important Limitation

A passing baseline gate means **no type-safety regression**. It does not mean the codebase has zero type errors. Only a budget of `0` supports that claim.
