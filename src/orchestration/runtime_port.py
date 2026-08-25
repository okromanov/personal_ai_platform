"""Runtime port abstraction (ARC_CMP_003).

Stable, framework-agnostic boundary between the platform and a swappable
agent execution environment. Per ADR_002, the concrete environment is not
fixed by this contract -- which environment to use is a separate, still
open decision (ADR_006). A RuntimePort implementation never sees owner
secrets, the emergency switch, or canonical long-lived memory directly:
the orchestrator supplies only the minimally sufficient task input.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.channels.base import TaskMessage


class RuntimePortError(Exception):
    """Raised when execution cannot even be attempted (environment unavailable)."""


@dataclass(frozen=True)
class RuntimeResult:
    """Normalized outcome of executing a task through a RuntimePort.

    Attributes:
        output: Text response produced for the owner.
        succeeded: Whether execution completed without error.
        error_message: Present when succeeded is False.
    """

    output: str
    succeeded: bool = True
    error_message: str | None = None


class RuntimePort(ABC):
    """Abstract contract for a swappable agent execution environment.

    Implementations own the specifics of a concrete agent framework or
    model call. Swapping the implementation must not require changes to
    the channel, owner-control, or data contracts above this boundary
    (SYS_003).
    """

    @abstractmethod
    async def execute(self, message: TaskMessage) -> RuntimeResult:
        """Run one task to completion through the connected environment.

        Args:
            message: Normalized task input from a channel.

        Returns:
            RuntimeResult with the produced output, or a controlled
            failure (`succeeded=False`) for an expected error such as a
            model or tool failure.

        Raises:
            RuntimePortError: If the environment itself cannot be reached
                at all. Expected task-level failures should be returned
                as a failed RuntimeResult instead of raising.
        """
