# Security Code Audit Skill

**ID:** security_audit  
**Type:** Blocking Quality Gate  
**Frequency:** Every push, every pull request, weekly, or on-demand  
**Framework:** LLM-agnostic

## Purpose

Run static application security testing (SAST) using Bandit to detect common security vulnerabilities and anti-patterns in Python code.

## Scope

Checks all Python scripts in:
- `operations/scripts/` - Automation and generation tools
- `operations/tests/` - Unit test suite
- `src/` - Application source code (if present)

Detects:
- ✅ SQL injection vulnerabilities
- ✅ Hardcoded credentials and secrets
- ✅ Insecure deserialization (pickle, marshal, etc.)
- ✅ Use of hardcoded temporary files
- ✅ Insecure random number generators
- ✅ Unsafe YAML loading
- ✅ Shell injection risks
- ✅ Assertion misuse for validation

## Run

```bash
python3.12 -m pip install -r operations/quality/requirements_dev.txt
python3.12 -m bandit -r operations/scripts operations/tests --severity-level medium --format json --output runtime/security_audit.json
python3.12 -m bandit -r operations/scripts operations/tests --severity-level medium
```

## Success Criteria

- ✅ 0 HIGH and MEDIUM severity issues in production code (`operations/scripts`)
- ✅ 0 HIGH severity issues in test code
- ✅ Medium/Low findings are documented and justified in code comments
- ✅ No hardcoded credentials or API keys
- ✅ All data deserialization uses safe methods

## Output Format

Generate report with:
1. **Summary:** Pass/Fail, critical findings count
2. **Issues found:** File, line number, issue type, severity, description
3. **Risk assessment:** Which vulnerabilities are exploitable in current architecture
4. **Recommendations:** Remediation steps per issue
5. **Evidence:** JSON report from bandit for CI artifacts

## When to Run

- **Automatic:** Every push to any branch and on every PR
- **Manual:** When dependencies change or after security incident
- **On-demand:** Before production deployment

## Failure Actions

If HIGH severity issues found:
1. Fix immediately before merging
2. Create security incident report if exploitable
3. Add regression test to prevent similar issues
4. Review code audit practices

## Configuration

The enforced Bandit configuration uses the default checks. CI runs are in `severity-level medium` to catch nuanced issues. Individual tests can be skipped with `# nosec` comment but only with explicit justification.

Do not suppress findings without documented rationale.

## Related Skills

- [code_quality_check](code_quality_check.md) - Complementary code audit
- [python_lint_check](python_lint_check.md) - Lint and style checks
- [pre_commit_validation](pre_commit_validation.md) - Fast pre-commit gate
