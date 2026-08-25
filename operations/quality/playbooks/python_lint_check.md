---
id: python_lint_check
type: guide
document_state: current
version: 1.0
updated: 2026-08-25
---

# Python Lint Check Skill

**ID:** python_lint_check  
**Type:** Periodic Quality Check  
**Frequency:** Every push, every pull request, or on-demand  
**Framework:** LLM-agnostic (Claude, other LLMs, or CLI automation)

## Purpose

Static code analysis and style checking using Ruff to catch common issues, enforce consistent style, and prevent anti-patterns.

## Scope

Checks all Python scripts in:
- `operations/scripts/` - Automation and generation tools
- `operations/tests/` - Unit test suite

Verifies:
- ✅ PEP 8 style compliance
- ✅ Import organization (unused, circular, etc.)
- ✅ Undefined names
- ✅ Common mistakes and pitfalls
- ✅ Complexity warnings

## Execution Steps

1. **Install the pinned development tools:**
   ```bash
   python3.12 -m pip install -r operations/quality/requirements_dev.txt
   ```

2. **Run Ruff check:**
   ```bash
   python3.12 -m ruff check operations/scripts operations/tests --show-fixes
   ```

3. **Run Ruff format check (dry-run):**
   ```bash
   python3.12 -m ruff format operations/scripts operations/tests --check --diff
   ```

4. **Auto-fix simple issues:**
   ```bash
   python3.12 -m ruff check operations/scripts operations/tests --fix
   python3.12 -m ruff format operations/scripts operations/tests
   ```

## Success Criteria

- ✅ 0 high-severity lint issues
- ✅ Code follows PEP 8 style
- ✅ No undefined names
- ✅ No circular imports
- ✅ No unused variables/imports (unless annotated with `_`)

## Output Format

Generate report with:
1. **Summary:** Pass/Fail, critical findings count
2. **Issues found:** File, line number, rule ID, description
3. **Fixable issues:** Which can be auto-fixed vs manual review
4. **Style violations:** PEP 8 and formatting issues
5. **Recommendations:** Priority order for fixes

## When to Run

- **Automatic:** Every push and pull request, via `run_suite.py`
- **Manual:** After substantial code changes
- **On-demand:** Before production deployment
- **In PR:** As pre-merge validation (if CI integrated)

## Failure Actions

If issues found:
1. Document exact location and severity
2. Distinguish between blocking (must fix) and cleanup (should fix)
3. Auto-fix simple issues (import reordering, etc.)
4. Create PR/issues for complex violations
5. Update linter configuration if needed

## Configuration

The enforced Ruff configuration is in the root `pyproject.toml`. CI and local runs must use the pinned Ruff version from [`operations/quality/requirements_dev.txt`](../../../operations/quality/requirements_dev.txt).

Do not broaden the rule set without fixing the resulting findings in the same change. This keeps the gate green and prevents a permanently failing CI baseline.

## Related Skills

- [code_quality_check](code_quality_check.md) - Complementary code audit
- [python_type_check](python_type_check.md) - Type safety verification
- [unit_tests](unit_tests.md) - Test execution
