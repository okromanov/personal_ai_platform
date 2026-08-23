#!/bin/bash
# Pre-commit hook: regenerate dashboards if task files changed
# Triggered before commit to ensure project_status.md and tasks.md stay in sync
#
# This hook is intentionally non-blocking (a failure here must not stop a
# commit), but non-blocking must never mean invisible: every failure is
# printed to stderr so the developer sees it locally instead of only in CI.

set -uo pipefail

# Check if any task or test files were staged
if git diff --cached --name-only 2>/dev/null | grep -qE "^work/(tasks|tests|m[0-9]+)/"; then
    echo "📊 Detected changes in task/test files, regenerating dashboards..."

    if command -v python3 >/dev/null 2>&1; then
        if ! python3 operations/scripts/status/generate_project_status.py; then
            echo "⚠️  generate_project_status.py failed (see output above) — dashboard may be stale" >&2
        fi
        if ! python3 operations/scripts/documents/generate.py --all; then
            echo "⚠️  documents/generate.py --all failed (see output above) — generated/ may be stale" >&2
        fi

        # Auto-add regenerated files if they changed
        if ! git diff --quiet project_status.md 2>/dev/null || \
           ! git diff --quiet tasks.md 2>/dev/null || \
           ! git diff --quiet generated/ 2>/dev/null; then
            echo "⚡ Dashboard changes detected, adding to commit..."
            git add project_status.md tasks.md generated/
        fi
    fi
fi

# Increment file versions for modified .md files. Deleted files have nothing
# to version-bump or re-add, so exclude them (git diff --cached lists them too).
if command -v python3 >/dev/null 2>&1; then
    modified_md=()
    while IFS= read -r path; do
        [ -f "$path" ] && modified_md+=("$path")
    done < <(git diff --cached --name-only -- '*.md' 2>/dev/null)
    if [ "${#modified_md[@]}" -gt 0 ]; then
        if ! python3 operations/scripts/versioning/increment_file_version.py "${modified_md[@]}"; then
            echo "⚠️  increment_file_version.py failed (see output above) — versions may not be bumped" >&2
        fi
        git add "${modified_md[@]}"
    fi
fi

exit 0
