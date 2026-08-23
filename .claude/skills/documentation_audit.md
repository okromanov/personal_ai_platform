# Documentation Audit Skill

**ID:** documentation_audit  
**Type:** Periodic Quality Check  
**Frequency:** Every push, every pull request, or on-demand  
**Framework:** LLM-agnostic (Claude, other LLMs, or CLI automation)

## Purpose

Comprehensive audit of all Markdown documentation files for logical consistency, correctness, MECE compliance, metadata honesty, and readability.

## Scope

Checks the current set of primary documentation files (excluding generated views, templates, and test specifications where appropriate):
- Specifications (business requirements, threat model, architecture, infrastructure)
- Operations procedures (change process, semantic review, acceptance, lifecycle)
- Authority documents (project rules, AGENTS, milestones)
- Owner interface (dashboard, status, reference)
- ADR decisions and their traceability

## Execution Steps

1. **Run comprehensive check:**
   ```bash
   python3.12 operations/scripts/documents/check.py --all
   ```
   Validates: structure, metadata, traceability, document policy, links, generated files

2. **Analyze findings:**
   - Count CRITICAL (blocks development), HIGH (significant issues), MEDIUM/LOW (polish)
   - Identify patterns: metadata dishonesty, broken references, inconsistent terminology
   - Check for "two sources of truth" problems
   - Verify dependency hierarchies match documentation

3. **Report issues by category:**
   - **Logic problems:** Inconsistent procedures, contradictory guidance
   - **Consistency issues:** Duplicate content, misaligned references
   - **MECE violations:** Overlapping categories, incomplete coverage
   - **Clarity issues:** Ambiguous definitions, missing examples
   - **Metadata problems:** Outdated dates, incorrect versioning

## Success Criteria

- ✅ `check.py --all` returns: `errors=0, warnings=0`
- ✅ No files with metadata dishonesty (updated dates)
- ✅ All ADR have valid `traces_to`; the explicit milestone ID `m01` is allowed only for ADR accepted atomically with the foundation
- ✅ No broken cross-references

## Output Format

Generate report with:
1. Executive summary (pass/fail status)
2. Issues found (if any) with file paths and line numbers
3. Recommendations for fixes
4. Severity breakdown (CRITICAL/HIGH/MEDIUM/LOW)
5. Estimated time to resolution

## When to Run

- **Automatic:** Every push and pull request, via `check.py --all`
- **Manual:** After any documentation changes, before release
- **On-demand:** When inconsistencies are suspected

## Failure Actions

If issues found:
1. Document each issue with exact location and impact
2. Categorize by severity
3. Create action plan for fixes
4. Estimate resolution time
5. Recommend priority order for fixes

## Usage with Different LLMs/Frameworks

### With Claude (Claude Code / IDE)
```
/documentation_audit
```

### With Other LLMs or Automation
1. Read this skill file
2. Execute commands in section "Execution Steps"
3. Interpret results using section "Output Format"
4. Report findings according to "Success Criteria"

### With CLI/CI Automation (GitHub Actions, etc.)
```bash
python3.12 operations/scripts/documents/check.py --all
```

The complete repository gate, including unit tests and coverage, is owned by
`operations/scripts/quality/run_suite.py full`; this playbook does not duplicate it.

## Related Skills

- [code_quality_check](code_quality_check.md) - Complementary code audit
- [pre_commit_validation](pre_commit_validation.md) - Blocking checks before commits
