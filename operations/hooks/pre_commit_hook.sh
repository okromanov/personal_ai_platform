#!/usr/bin/env bash
# Compatibility entrypoint. The canonical hook lives with the repository QA playbooks.

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
exec bash "$PROJECT_ROOT/.claude/skills/pre_commit_hook.sh"
