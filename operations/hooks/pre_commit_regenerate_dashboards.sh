#!/bin/bash
# Pre-commit hook: regenerate dashboards if any tracked Markdown doc changed
# Triggered before commit to ensure project_status.md, tasks.md and
# generated/* stay in sync
#
# This hook is intentionally non-blocking (a failure here must not stop a
# commit), but non-blocking must never mean invisible: every failure is
# printed to stderr so the developer sees it locally instead of only in CI.

set -uo pipefail

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
PYTHON="$(find_python || true)"

# Increment file versions for modified .md files first. Dashboards below embed
# each document's version number, so they must be regenerated *after* this
# step — otherwise they'd snapshot the pre-bump version and immediately drift
# from what generate.py would produce on the very next run. Deleted files have
# nothing to version-bump or re-add, so exclude them (git diff --cached lists
# them too).
modified_md=()
if [ -n "$PYTHON" ]; then
    while IFS= read -r path; do
        [ -f "$path" ] && modified_md+=("$path")
    done < <(git diff --cached --name-only -- '*.md' 2>/dev/null)
    if [ "${#modified_md[@]}" -gt 0 ]; then
        if ! "$PYTHON" operations/scripts/versioning/increment_file_version.py "${modified_md[@]}"; then
            echo "⚠️  increment_file_version.py failed (see output above) — versions may not be bumped" >&2
        fi
        git add "${modified_md[@]}"
    fi
else
    echo "⚠️  No Python 3.12+ interpreter found — version bump and dashboard regeneration skipped" >&2
fi

# Regenerate whenever any staged Markdown doc changed. generated/*
# (document_index.md, repository_structure.md, traceability_matrix.md,
# test_catalog.md) reflect every tracked .md's frontmatter (id/type/version/
# state), not just work/tasks|tests|mXX — a version bump on e.g. AGENTS.md or
# an ADR drifts them exactly the same way a TASK/TEST change does, so scoping
# this to work/* alone left those cases unregenerated until CI caught them.
if [ "${#modified_md[@]}" -gt 0 ]; then
    echo "📊 Detected changes in tracked Markdown docs, regenerating dashboards..."

    if [ -n "$PYTHON" ]; then
        # documents/generate.py --all is the single entry point that rebuilds
        # project_status.md, tasks.md and generated/*; there's nothing
        # further to call.
        if ! "$PYTHON" operations/scripts/documents/generate.py --all; then
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

exit 0
