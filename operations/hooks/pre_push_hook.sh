#!/usr/bin/env bash
# Canonical pre-push hook for personal_ai_platform.
# Install: cp operations/hooks/pre_push_hook.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
#
# Runs the same full quality profile CI enforces (mypy, Ruff format, coverage
# policy, Bandit, Vulture, AST code analysis) before code leaves the machine,
# so a regression is caught locally instead of on the next CI run. Actionlint,
# ShellCheck, pip-audit and Gitleaks stay CI-only: they fetch pinned external
# binaries over the network, which does not belong in a local git hook.

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
echo "Running pre-push validation with $PYTHON"

echo "  [1/2] Development tools"
if ! "$PYTHON" -m ruff --version >/dev/null 2>&1; then
    echo "ERROR: install development tools: $PYTHON -m pip install -r operations/quality/requirements_dev.txt" >&2
    exit 1
fi

echo "  [2/2] Canonical full quality suite"
"$PYTHON" operations/scripts/quality/run_suite.py full

echo "Pre-push validation passed."
