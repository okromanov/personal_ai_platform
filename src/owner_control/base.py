"""Base owner control abstraction (ARC_CMP_002).

Verifies identity, owner rules, emergency state and applicable conditions
before a task starts or continues, and again before a sensitive action
executes. The emergency switch has priority over the runtime, scheduler,
retries, tool gateway and models -- none of those components has a bypass
to resources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class OwnerControlError(Exception):
    """Base exception for owner-control-related errors."""


class IdentityRejected(OwnerControlError):
    """Raised when a subject is not the recognized owner (SEC_CTL_001)."""


class EmergencyStopActive(OwnerControlError):
    """Raised when the independent emergency switch is active (SEC_CTL_002)."""


class ActionClass(Enum):
    """Impact classification of a candidate action (per SEC_CTL_008)."""

    READ = "read"
    WRITE_EXTERNAL = "write_external"
    DESTRUCTIVE = "destructive"
    ADMIN = "admin"


SENSITIVE_ACTION_CLASSES = frozenset(
    {ActionClass.WRITE_EXTERNAL, ActionClass.DESTRUCTIVE, ActionClass.ADMIN}
)


@dataclass(frozen=True)
class AuthorizationDecision:
    """Outcome of an authorization check for a candidate action.

    Attributes:
        authorized: Whether the action may proceed now.
        action_id: Caller-supplied identifier used to detect duplicate execution.
        reason: Short machine-readable reason for the decision.
        decided_at: When the decision was made.
    """

    authorized: bool
    action_id: str
    reason: str
    decided_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class OwnerControl(ABC):
    """Abstract contract for owner control (ARC_CMP_002).

    Checked before a task starts or continues, and again before a sensitive
    external action executes. Does not own task orchestration, memory, or
    tool execution -- only whether the platform is currently permitted to
    proceed on behalf of the owner.
    """

    @abstractmethod
    def verify_identity(self, subject_id: str) -> None:
        """Reject a subject that is not the recognized owner.

        Args:
            subject_id: Channel-supplied identity of the sender (e.g. Telegram user id).
                Identity is never inferred from message text.

        Raises:
            IdentityRejected: If subject_id is not the configured owner identity.
        """

    @abstractmethod
    def check_emergency_stop(self) -> None:
        """Raise if the independent emergency switch is currently active.

        Raises:
            EmergencyStopActive: If the switch is on.
        """

    @abstractmethod
    def authorize_sensitive_action(
        self,
        action_id: str,
        action_class: ActionClass,
        params: dict[str, Any],
        *,
        confirmed: bool = False,
    ) -> AuthorizationDecision:
        """Authorize (or reject) a candidate action before it executes.

        For `ActionClass.READ`, the action is authorized immediately. For the
        sensitive classes (`WRITE_EXTERNAL`, `DESTRUCTIVE`, `ADMIN`), a first
        call with `confirmed=False` records the exact parameters as pending
        and is rejected; the action is authorized only on a second call with
        `confirmed=True` and the identical `action_id`/`action_class`/`params`.
        Once authorized, the same `action_id` is rejected as a duplicate on
        any further call, so a retry cannot silently repeat the effect.

        Args:
            action_id: Unique identifier of the candidate action.
            action_class: Impact classification of the action.
            params: Concrete significant parameters of the action.
            confirmed: Whether the owner has confirmed these exact parameters.

        Returns:
            AuthorizationDecision describing whether the action may proceed.
        """
