---
id: code_quality_check
type: guide
document_state: current
version: 1.3
updated: 2026-09-02
---

# Code Quality Check Skill

**ID:** code_quality_check  
**Type:** Periodic Quality Check  
**Frequency:** Automated static subset on every repository event (push/PR/merge candidate); semantic audit after substantial changes or on-demand
**Framework:** LLM-agnostic (Claude, other LLMs, or CLI automation)

## Purpose

Comprehensive audit of Python scripts and code for production-readiness, including stub detection, dead code removal, and general code quality.

## Scope

Checks all Python scripts in:
- `operations/scripts/` - Automation and generation tools
- `operations/tests/` - Unit test suite
- Configuration files (JSON, YAML, TOML, pinned TXT dependency manifests)

Verifies:
- ✅ No hardcoded placeholders or stub implementations
- ✅ All imports are used (except PEP 563 type hints)
- ✅ No dead code or unused functions
- ✅ Error handling is appropriate (not over-protected)
- ✅ Critical paths fully implemented

## Execution Steps

**UPDATED (v3.4):** Uses AST analysis instead of regex for accuracy.

1. **Run advanced code analyzer (AST-based):**
   ```bash
   python3.12 operations/scripts/quality/code_analyzer.py > runtime/code_analysis.json
   ```
   
   This detects:
   - Functions with only `pass` (true stubs, not legitimate exception handlers)
   - `raise NotImplementedError` in production code
   - TODOs/FIXMEs in function docstrings (not in file paths or URLs)

   Only stub findings are blocking (exit 1). Неиспользуемые импорты — не его
   задача: их ловит Ruff `F401`, выбранный в `pyproject.toml` и блокирующий
   в шаге «Ruff lint» канонического набора. Собственный детектор в
   `code_analyzer.py` дублировал это правило, но не мог уронить гейт, и был
   удалён вместе с не имевшим порога и потребителей счётчиком цикломатической
   сложности.

2. **Search for hardcoded values (regex-based, human review):**
   ```bash
   grep -r "test_data\|temp_file\|demo_config\|stub_" --include="*.py" operations/scripts/ | grep -v "# " | grep -v mock
   ```
   
   **Note:** This is a suggestion list requiring manual verification to avoid false positives.

3. **Security-focused checks (Bandit):**
   ```bash
   python3.12 -m bandit -r operations/scripts --severity-level medium
   ```
   
   Detects hardcoded secrets, SQL injection patterns, insecure deserialization.

4. **Verify critical paths:**
   - `operations/scripts/acceptance/apply.py` - Must have complete state machine
   - `operations/scripts/status/generate_project_status.py` - Must handle all milestone states
   - `operations/scripts/quality/registry.py` - Must validate all required fields
   - `operations/scripts/documents/check.py` - Must have comprehensive validation rules

5. **Run deterministic security and workflow checks:**
   ```bash
   python3.12 -m pip_audit --requirement operations/quality/requirements_dev.txt
   actionlint -shellcheck=shellcheck
   shellcheck operations/hooks/pre_commit_hook.sh operations/hooks/pre_push_hook.sh
   gitleaks dir . --redact --no-banner
   ```

   The pinned Actionlint and Gitleaks binaries are downloaded and SHA-256 verified by GitHub Actions; they are not silently skipped when unavailable.

6. **Analyze code metrics** (человеческое суждение, не автоматический порог):
   - Average function length (prefer <50 lines)
   - Cyclomatic complexity (prefer <10)
   - Import organization (stdlib, third-party, local) — механически проверяется
     правилом Ruff `I`

## Success Criteria

- ✅ 0 TODO/FIXME markers outside templates
- ✅ 0 hardcoded stub/test/demo values in production code
- ✅ 0 unused imports
- ✅ 0 unused functions or dead code paths
- ✅ All critical paths fully implemented (no pass-only functions)
- ✅ No obvious security anti-patterns

## Output Format

Generate report with:
1. **Summary:** Pass/Fail, critical findings count
2. **Stubs found:** File, line number, context
3. **Dead code:** Unused functions/attributes from the Vulture step; unused
   imports from Ruff `F401`
4. **Security concerns:** Patterns to review, risk level
5. **Code quality metrics:** Function complexity and import hygiene — read
   from the sources above, not from `code_analysis.json`
6. **Recommendations:** Specific improvements with priority

## When to Run

- **Automatic:** Ruff, mypy, coverage and deterministic repository checks run on every push/PR/merge candidate
- **Manual:** This reasoning-based playbook runs after substantial code changes; it is not falsely represented as an unattended LLM review
- **On-demand:** Before production deployment
- **In PR:** As pre-merge validation (if CI integrated)

## Failure Actions

If issues found:
1. Document exact location and severity
2. Distinguish between blocker (must fix) and cleanup (should fix)
3. Create PR/issues for each distinct problem
4. Estimate fix time per issue
5. Flag security issues for priority handling

## Quality Baseline

Do not record a permanent star rating or a manually maintained issue count in this playbook. The current result is the output of the exact CI run being inspected. A clean historical run is not evidence for a later SHA.

## Usage with Different LLMs/Frameworks

### With Claude (Claude Code / IDE)
```
/code_quality_check
```

### With Other LLMs or Automation
1. Read this skill file
2. Execute grep commands and checks in "Execution Steps"
3. Analyze results against "Success Criteria"
4. Generate report using "Output Format"

### With CLI/CI Automation (GitHub Actions, Jenkins, etc.)
```bash
# Run grep patterns for stubs
grep -r "TODO\|FIXME\|XXX\|HACK" --include="*.py" operations/scripts/ --exclude-dir=templates

# Check for dead code patterns
grep -r "pass$\|return None\|raise NotImplementedError" --include="*.py" operations/scripts/

# Verify critical paths exist and are implemented
```

## Related Skills

- [documentation_audit](documentation_audit.md) - Complementary documentation audit
- [pre_commit_validation](pre_commit_validation.md) - Blocking checks before commits
