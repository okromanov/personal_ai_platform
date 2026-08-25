---
id: documentation_rules_detailed
type: guide
document_state: current
version: 1.0
updated: 2026-08-25
---

# Documentation Audit Rules - Detailed Reference

**Purpose:** Explain the exact rules and patterns checked by `operations/scripts/documents/check.py`

## Front Matter Requirements

All Markdown documents must have valid YAML front matter (between `---` markers):

```yaml
---
title: Document Title
updated: 2026-08-24
version: 1.1
type: specification | procedure | authority | dashboard
traces_to: m01, m02  # Milestone IDs this document traces to
---
```

### Metadata Fields

| Field | Required | Format | Rules |
|-------|----------|--------|-------|
| `title` | YES | String | Max 100 chars, descriptive |
| `updated` | YES | YYYY-MM-DD | Must match actual edit date |
| `version` | YES | X.Y or X.Y.Z | Semver format |
| `type` | YES | Enum | One of: specification, procedure, authority, dashboard, decision, reference |
| `traces_to` | YES (for ADR) | Comma-separated IDs | Valid milestone IDs like m01, m02 |

### Metadata Dishonesty

**Definition:** Updated date or version number does not match actual changes

**Examples of violations:**
- Document body changed but `updated` date is old
- Breaking content change but `version` bumped from 1.0 to 1.1 (should be 2.0)
- Content is identical but `version` incremented

**Check:** Compares HEAD version against staged changes

## Cross-References and Links

### Internal Cross-References

Valid formats — a markdown link's `[text]` followed by its target in
parentheses (written here with a separating arrow so this reference itself
isn't parsed as a real link to a nonexistent path):

- `[Link text]` → `./path/to/file.md` — relative path from document
- `[Link text]` → `#section-anchor` — same document anchor
- `[Link text]` → `./other.md#anchor` — file + anchor

**Violations:**
- Links to non-existent files
- Links to deleted sections
- Broken anchor references

### External Links

**Validation:**
- HTTPS only (http:// is rejected)
- Valid domain format
- No hardcoded IPs for external links

## MECE (Mutually Exclusive Collectively Exhaustive) Compliance

**Definition:** Categories should not overlap and should cover all cases

### Where MECE is enforced:

1. **Milestone states:** `planning`, `in-progress`, `completed`, `archived`
   - No overlap, all states must be present
   
2. **Task types:** `feature`, `bugfix`, `refactor`, `documentation`
   - No document can be tagged as multiple types that overlap
   
3. **Severity levels:** `critical`, `high`, `medium`, `low`
   - Must be mutually exclusive
   - Coverage must be complete for any categorized items

### MECE Violations:

- A document marked as both `specification` AND `procedure`
- Task marked as both `feature` AND `refactor` (these overlap)
- Milestone states like `complete` and `completed` (inconsistent naming)
- Incomplete category coverage (some items unclassified)

**Exception:** Root [`m01`](../../../milestones.md#m01) milestone allowed without `traces_to` field (foundational)

## Consistency Rules

### Terminology

**Rule:** Consistent term usage across all documentation

**Violations:**
- Using "Task" and "task" interchangeably (inconsistent capitalization)
- Using "milestone", "phase", "stage" for same concept
- "Acceptance" vs "acceptability"

### Structure

**Rule:** Documents of same type must follow consistent structure

**Example - Procedure documents must have:**
1. Purpose section
2. Prerequisites section
3. Steps (numbered)
4. Success criteria
5. Rollback procedure

**Violation:** Procedure missing any section that others have

### Naming Conventions

**Authority documents** (must match exactly):
- [`project_rules.md`](../../../project_rules.md)
- [`AGENTS.md`](../../../AGENTS.md)
- [`operations/change_process.md`](../../../operations/change_process.md)
- Milestone definitions in specifications

**Specification documents:**
- [`specifications/business_requirements.md`](../../../specifications/business_requirements.md)
- [`specifications/threat_model.md`](../../../specifications/threat_model.md)
- [`specifications/system_specification.md`](../../../specifications/system_specification.md)
- [`specifications/architecture_baseline.md`](../../../specifications/architecture_baseline.md)
- [`specifications/infrastructure_baseline.md`](../../../specifications/infrastructure_baseline.md)

## Generated Files

**Definition:** Files created by scripts (not manually edited)

**Current generated files:**
- [`project_status.md`](../../../project_status.md) - Auto-generated from status script
- [`tasks.md`](../../../tasks.md) - Auto-generated from task registry
- [`generated/markdown_index.md`](../../../generated/markdown_index.md) - Index of all Markdown docs
- [`generated/non_markdown_index.md`](../../../generated/non_markdown_index.md) - Index of all non-Markdown files
- [`generated/repository_structure.md`](../../../generated/repository_structure.md) - Directory tree
- [`generated/traceability_matrix.md`](../../../generated/traceability_matrix.md) - Requirement traceability

**Rule:** Generated files must be bit-identical with last run

**Check:** `git diff --exit-code -- project_status.md tasks.md generated`

## Traceability Rules

### Requirement → ADR → Code Mapping

**Valid traces_to values:**
- Milestone IDs: [`m01`](../../../milestones.md#m01), [`m02`](../../../milestones.md#m02), [`m03`](../../../milestones.md#m03), etc.
- ADR IDs: `adr-001`, `adr-002`, etc. (optional, creates bidirectional link)

**Violations:**
- Invalid ID format (e.g., `adr_001` instead of `adr-001`)
- Tracing to non-existent milestone
- Circular trace dependencies

### Traceability Matrix

**Rule:** Every requirement in specifications/ must have at least one ADR

**Violation:** A requirement without `traces_to` anchor

**Check:** `operations/scripts/documents/check.py` validates this matrix

## Line-Level Rules

### Comments and TODOs

**Allowed in documentation:**
- `<!-- TODO: explain this section better -->` - Editorial notes
- `<!-- FIXME: broken link -->` - Known issues

**Not allowed:**
- Inline TODO outside comments: `> Fix this later in section X`
- Multiple TODOs without due date or owner

### Code Blocks

**Rule:** Code blocks must have language specified

**Valid:**
```python
def foo():
    pass
```

**Invalid:**
```
def foo():
    pass
```

**Rule:** Code examples must be syntactically valid (will be checked on ci)

## Output Severity Levels

| Level | Type | Blocks Merge |
|-------|------|-------------|
| CRITICAL | Logic error, broken reference, metadata dishonesty | YES |
| HIGH | MECE violation, inconsistency, malformed metadata | YES |
| MEDIUM | Minor clarity issues, style inconsistency | NO (warning) |
| LOW | Typos, formatting suggestions | NO (info) |

## Exceptions and Overrides

To override a check, add comment in document:

```markdown
<!-- suppress check: mece-violation reason: X and Y are not truly mutually exclusive in our context -->
```

**Valid suppression reasons must:**
1. Be explicit and documented
2. Include expected duration: `until <date>` or `until <milestone>`
3. Be reviewed before merge

## Validation Sequence

The checker runs in this order:

1. **Metadata validation** - Parse YAML front matter
2. **Link validation** - Check all references exist
3. **Structure validation** - Verify document structure matches type
4. **Consistency checks** - MECE, terminology, naming
5. **Traceability checks** - Valid milestone IDs, ADR links
6. **Generated files** - Drift detection

**Early exit:** CRITICAL errors stop at first violation

## Testing and CI Integration

All checks run in:
- `.github/workflows/project_check.yml` - Windows job via `check.py --all`
- Local pre-commit hook via `operations/hooks/pre_commit_hook.sh`

**Command:** `python3.12 operations/scripts/documents/check.py --all --json`

Output is JSON with severity, file, line, and remediation suggestion.
