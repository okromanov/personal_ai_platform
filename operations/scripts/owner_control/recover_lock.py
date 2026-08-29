"""Recover a sensitive-action lock left behind by a crashed process (AUD-013).

Never run this automatically or as part of any regular gate/hook. The lock is
fail-closed by design: authorize_sensitive_action() refuses to run while it
is held, which is correct as long as the holder might still be running. Only
run this after confirming out of band -- `ps`/`kill -0`, container/process
logs, deployment history -- that the process which held it is actually gone,
not merely slow. See operations/procedures/recover_stale_sensitive_action_lock.md
for the full runbook.

Usage:
    python3 -m operations.scripts.owner_control.recover_lock <state_dir> \\
        --confirm "REMOVE STALE OWNER CONTROL LOCK"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.owner_control import (
    RECOVERY_CONFIRMATION_PHRASE,
    StaleLockRecoveryError,
    recover_stale_sensitive_action_lock,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path, help="owner-control state directory")
    parser.add_argument(
        "--confirm",
        required=True,
        help=f"must be exactly: {RECOVERY_CONFIRMATION_PHRASE!r}",
    )
    args = parser.parse_args()
    try:
        recover_stale_sensitive_action_lock(args.state_dir, confirmation=args.confirm)
    except StaleLockRecoveryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Lock removed: {args.state_dir / 'owner_control_actions.lock'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
