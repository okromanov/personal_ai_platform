#!/bin/bash
# Pre-commit hook: regenerate dashboards if task files changed
# Triggered before commit to ensure project_status.md and tasks.md stay in sync

set -uo pipefail

# Check if any task or test files were staged
if git diff --cached --name-only 2>/dev/null | grep -qE "^work/(tasks|tests|m[0-9]+)/"; then
    echo "📊 Detected changes in task/test files, regenerating dashboards..."

    # Try to regenerate, but don't block commit on failure
    if command -v python3 >/dev/null 2>&1; then
        python3 operations/scripts/status/generate_project_status.py >/dev/null 2>&1 || true
        python3 operations/scripts/documents/generate.py --all >/dev/null 2>&1 || true

        # Auto-add regenerated files if they changed
        if ! git diff --quiet project_status.md 2>/dev/null || \
           ! git diff --quiet tasks.md 2>/dev/null || \
           ! git diff --quiet generated/ 2>/dev/null; then
            echo "⚡ Dashboard changes detected, adding to commit..."
            git add project_status.md tasks.md generated/ 2>/dev/null || true
        fi
    fi
fi

# Increment file versions for modified .md files
if command -v python3 >/dev/null 2>&1; then
    modified_md=$(git diff --cached --name-only -- '*.md' 2>/dev/null || echo "")
    if [ -n "$modified_md" ]; then
        python3 operations/scripts/versioning/increment_file_version.py $modified_md 2>/dev/null || true
        git add $modified_md 2>/dev/null || true
    fi
fi

exit 0
