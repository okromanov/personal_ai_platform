"""File-persisted emergency switch (SEC_CTL_002).

Stores owner-set emergency state outside the model process and outside any
swappable agent runtime: it lives in a file, not in memory, so it survives
process restart and does not depend on the model or runtime being available
or well-behaved.
"""

import json
from pathlib import Path


class EmergencySwitch:
    """Persisted on/off state for the independent emergency stop."""

    def __init__(self, state_path: Path) -> None:
        """Initialize the switch.

        Args:
            state_path: File used to persist the on/off state.
        """
        self._path = state_path

    def activate(self, reason: str = "") -> None:
        """Turn the emergency switch on.

        Args:
            reason: Optional human-readable reason, stored alongside the state.
        """
        self._write(active=True, reason=reason)

    def deactivate(self) -> None:
        """Turn the emergency switch off."""
        self._write(active=False, reason="")

    def is_active(self) -> bool:
        """Return whether the switch is currently on.

        A missing or unreadable state file is treated as inactive rather than
        raising, so a fresh deployment starts in a normally-operating state.
        """
        if not self._path.is_file():
            return False
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False
        return bool(data.get("active", False))

    def _write(self, *, active: bool, reason: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"active": active, "reason": reason}),
            encoding="utf-8",
        )
