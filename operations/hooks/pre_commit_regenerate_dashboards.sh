#!/bin/bash
# Pre-commit hook: regenerate dashboards if task files changed
# Triggered before commit to ensure project_status.md and tasks.md stay in sync

set -euo pipefail

# Check if any task or test files were staged
if git diff --cached --name-only | grep -qE "^work/(tasks|tests|m[0-9]+)/"; then
    echo "📊 Detected changes in task/test files, regenerating dashboards..."

    python3 operations/scripts/status/generate_project_status.py || true
    python3 operations/scripts/documents/generate.py --all || true

    # Auto-add regenerated files if they changed
    if git diff --exit-code project_status.md >/dev/null 2>&1 || \
       git diff --exit-code tasks.md >/dev/null 2>&1 || \
       git diff --exit-code generated/ >/dev/null 2>&1; then
        echo "⚡ Dashboard changes detected, adding to commit..."
        git add project_status.md tasks.md generated/ || true
    fi
fi

# Increment file versions for modified files
if python3 operations/scripts/versioning/increment_file_version.py $(git diff --cached --name-only -- '*.md') 2>/dev/null; then
    echo "📝 File versions updated"
    git add $(git diff --cached --name-only -- '*.md') || true
fi

exit 0
