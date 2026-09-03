#!/bin/bash
# Pre-commit hook: validate template contracts and regenerate project_status.md
# if any tracked Markdown document changed.
#
# This is an integrity step, not a best-effort convenience: a failed version
# bump or regeneration must block the commit rather than leave plausible but
# stale generated files behind.

set -euo pipefail

# ADR_001 requires Python 3.12+; a bare `python3` can resolve to an older
# system interpreter (e.g. 3.11), under which documents/generate.py's own
# require_supported_python() refuses to run. Resolve the same way
# operations/hooks/pre_commit_hook.sh does so this step isn't silently skipped
# just because the environment's default `python3` is too old.
find_python() {
    for candidate in python3.14 python3.13 python3.12 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c \
            'import sys; raise SystemExit(sys.version_info < (3, 12))' 2>/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}
PYTHON="$(find_python)"

"$PYTHON" operations/scripts/documents/template_contracts.py

# Increment file versions for modified .md files first. Dashboards below embed
# each document's version number, so they must be regenerated *after* this
# step — otherwise they'd snapshot the pre-bump version and immediately drift
# from what generate.py would produce on the very next run. Deleted files have
# nothing to version-bump or re-add, so exclude them (git diff --cached lists
# them too).
modified_md=()
version_bump_md=()
while IFS= read -r path; do
    if [ -f "$path" ]; then
        modified_md+=("$path")
        # A manually updated version is already the intended semantic bump.
        # Only unchanged versions need the hook's automatic increment.
        if git cat-file -e "HEAD:$path" 2>/dev/null; then
            head_version="$(git show "HEAD:$path" | sed -n '/^---$/,/^---$/s/^version:[[:space:]]*//p' | head -n 1)"
            staged_version="$(git show ":$path" | sed -n '/^---$/,/^---$/s/^version:[[:space:]]*//p' | head -n 1)"
            if [ "$head_version" = "$staged_version" ]; then
                version_bump_md+=("$path")
            fi
        fi
    fi
done < <(git diff --cached --name-only -- '*.md' 2>/dev/null)
if [ "${#version_bump_md[@]}" -gt 0 ]; then
    "$PYTHON" operations/scripts/versioning/increment_file_version.py "${version_bump_md[@]}"
    git add "${version_bump_md[@]}"
fi

# Regenerate the owner dashboard whenever a staged Markdown document changed.
if [ "${#modified_md[@]}" -gt 0 ]; then
    echo "📊 Detected changes in tracked Markdown docs, regenerating project status..."

    # documents/generate.py --all intentionally rebuilds only the registered
    # owner dashboard. It never creates TASK cards or diagnostic indexes.
    "$PYTHON" operations/scripts/documents/generate.py --all

    if ! git diff --quiet project_status.md 2>/dev/null; then
        echo "⚡ Project status changed, adding it to commit..."
        git add project_status.md
    fi
fi
