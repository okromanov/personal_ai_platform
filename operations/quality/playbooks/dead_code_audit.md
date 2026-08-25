---
id: dead_code_audit
type: guide
document_state: current
version: 1.0
updated: 2026-08-25
---

# Dead Code and Duplication Audit

**ID:** dead_code_audit  
**Type:** Quality Check  
**Frequency:** Every push, every pull request, or on-demand  
**Framework:** LLM-agnostic

## Purpose

Detect and remove unused code, functions, imports, and variables to maintain code health. Identify code duplication for refactoring opportunities.

## Scope

Checks all Python scripts in:
- `operations/scripts/` - Automation and generation tools
- `operations/tests/` - Unit test suite
- `src/` - Application source code

Detects:
- ✅ Unused functions and methods
- ✅ Unused variables and imports
- ✅ Unreachable code
- ✅ Code duplication (copy-paste patterns)
- ✅ Orphaned function arguments

## Run

```bash
python3.12 -m pip install -r operations/quality/requirements_dev.txt
python3.12 -m vulture operations/scripts operations/tests --min-confidence 80
python3.12 -m pylint --disable=all --enable=duplicate-code operations/scripts operations/tests
```

### Detailed Analysis

```bash
# Find unused functions with 80%+ confidence
python3.12 -m vulture operations/scripts operations/tests --min-confidence 80 --json > runtime/dead_code.json

# Generate complexity metrics
python3.12 -m radon cc operations/scripts -a --json > runtime/complexity.json

# Find duplicate code blocks
python3.12 -m pylint --duplicate-code operations/scripts --output-format=json > runtime/duplicates.json
```

## Success Criteria

- ✅ 0 unused functions in production code
- ✅ 0 unused variables (unless prefixed with `_` for intentional ignoring)
- ✅ 0 unreachable code paths
- ✅ Duplication ratio < 5% (tracked via CI metrics)
- ✅ Functions with duplication > 100 lines refactored into shared utility

## Output Format

Generate report with:
1. **Summary:** Total findings, grouped by type
2. **Unused code:** Function/variable name, file, line, recommendation
3. **Duplications:** Location pairs, similarity percentage, refactoring suggestion
4. **Metrics:** Lines of code per module, duplication ratio, complexity score
5. **Recommendations:** Priority order for cleanup

## When to Run

- **Automatic:** Every push and pull request, via `run_suite.py full`
- **Manual:** After refactoring or adding large features
- **On-demand:** Before major release
- **In PR:** For substantial changes (>200 lines)

## Failure Actions

Unused functions (HIGH confidence):
1. Delete if truly unused
2. If intentional, document with comment and `# pylint: disable=unused-argument`
3. Create issue if it's planned for future use

Code duplication (>100 lines):
1. Extract to shared utility function
2. Update all call sites
3. Add tests for the utility

## Configuration

### Vulture settings:
- `min-confidence 80`: High confidence (reduces false positives)
- Ignores common patterns (fixtures, mocks, etc.)

### Pylint duplicate-code:
- `min-similarity-lines: 5` (blocks of 5+ identical lines)
- Detects cross-module duplication

### Radon complexity:
- Cyclomatic complexity > 10: WARNING
- Cognitive complexity > 15: ERROR

## Related Skills

- [code_quality_check](code_quality_check.md) - Comprehensive code audit
- [python_lint_check](python_lint_check.md) - Lint and style checks
