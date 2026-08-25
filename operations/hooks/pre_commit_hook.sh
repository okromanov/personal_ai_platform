#!/usr/bin/env bash
# Canonical pre-commit hook for personal_ai_platform.
# Install: cp operations/hooks/pre_commit_hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

find_python() {
    for candidate in python3.14 python3.13 python3.12 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c \
            'import sys; raise SystemExit(sys.version_info < (3, 12))'; then
            echo "$candidate"
            return 0
        fi
    done
    echo "ERROR: Python 3.12+ is required." >&2
    return 1
}

PYTHON="$(find_python)"
echo "Running pre-commit validation with $PYTHON"

echo "  [1/5] Auto-fix cross-references"
mapfile -t staged_md < <(git diff --cached --name-only --diff-filter=ACM -- '*.md')
if [ "${#staged_md[@]}" -gt 0 ]; then
    if ! "$PYTHON" -m operations.scripts.documents.links "${staged_md[@]}"; then
        echo "⚠️  Some cross-references could not be auto-linked (see output above) — fix them manually" >&2
    fi
    git add "${staged_md[@]}"
fi

echo "  [2/5] Authority document versions"
AUTHORITY_DOCS=(
  "project_rules.md"
  "AGENTS.md"
  "operations/change_process.md"
  "specifications/business_requirements.md"
  "specifications/threat_model.md"
  "specifications/system_specification.md"
  "specifications/architecture_baseline.md"
  "specifications/infrastructure_baseline.md"
)
body_after_front_matter() {
  awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2{print}'
}
for doc in "${AUTHORITY_DOCS[@]}"; do
    if git diff --cached -- "$doc" | grep -q '^+'; then
        old_version="$(git show HEAD:"$doc" 2>/dev/null | sed -n 's/^version: //p' | head -1)"
        new_version="$(git show :"$doc" 2>/dev/null | sed -n 's/^version: //p' | head -1)"
        old_body="$(git show HEAD:"$doc" 2>/dev/null | body_after_front_matter)"
        new_body="$(git show :"$doc" 2>/dev/null | body_after_front_matter)"
        if [ -n "$old_version" ] && [ "$old_version" = "$new_version" ] \
            && [ "$old_body" != "$new_body" ]; then
            echo "ERROR: $doc changed semantically without a version bump ($old_version)." >&2
            exit 1
        fi
    fi
done

echo "  [3/5] Development tools"
if ! "$PYTHON" -m ruff --version >/dev/null 2>&1; then
    echo "ERROR: install development tools: $PYTHON -m pip install -r operations/quality/requirements_dev.txt" >&2
    exit 1
fi

echo "  [4/5] Canonical fast quality suite"
"$PYTHON" operations/scripts/quality/run_suite.py fast

echo "  [5/5] Auto-regenerate dashboards and increment versions"
bash operations/hooks/pre_commit_regenerate_dashboards.sh || true

echo "Pre-commit validation passed."
