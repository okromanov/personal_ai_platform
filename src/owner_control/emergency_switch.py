"""File-persisted emergency switch (SEC_CTL_002).

Stores owner-set emergency state outside the model process and outside any
swappable agent runtime: it lives in a file, not in memory, so it survives
process restart and does not depend on the model or runtime being available
or well-behaved.
"""

from pathlib import Path

from .base import EmergencySwitchStateError
from .state_io import atomic_write_json, read_json_object


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

        A missing file represents an explicit fresh-deployment default. An
        existing file that cannot be trusted raises instead of failing open.
        """
        if not self._path.is_file():
            return False
        try:
            data = read_json_object(self._path)
        except ValueError as exc:
            raise EmergencySwitchStateError("emergency switch state is unreadable") from exc
        active = data.get("active")
        if not isinstance(active, bool):
            raise EmergencySwitchStateError("emergency switch state has no boolean 'active'")
        return active

    def _write(self, *, active: bool, reason: str) -> None:
        atomic_write_json(self._path, {"active": active, "reason": reason})
