"""Base channel abstraction (ARC_CMP_001).

Defines the stable contract for input/output normalization across all
supported interfaces. Each channel implementation transforms user input
into normalized TaskMessage and sends responses back through the same
interface without owning business logic, memory, or permissions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class TaskState(Enum):
    """Observable task lifecycle states (SYS_001)."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChannelError(Exception):
    """Base exception for channel-related errors."""

    pass


@dataclass
class TaskMessage:
    """Normalized task message from any channel (ARC_CMP_001 output).

    Attributes:
        task_id: Unique identifier for this task execution (per SYS_001)
        channel_type: Source channel (telegram, web, cli, voice)
        user_input: Normalized user input text
        metadata: Additional context (user_id, timestamp, etc.)
        state: Current observable state of the task
    """

    task_id: str = field(default_factory=lambda: str(uuid4()))
    channel_type: str = field(default="unknown")
    user_input: str = field(default="")
    metadata: dict[str, Any] = field(default_factory=dict)
    state: TaskState = field(default=TaskState.PENDING)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = field(default=None)
    error_message: Optional[str] = field(default=None)

    def mark_running(self) -> None:
        """Update state to running."""
        self.state = TaskState.RUNNING

    def mark_completed(self) -> None:
        """Update state to completed."""
        self.state = TaskState.COMPLETED
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        """Update state to failed with error message."""
        self.state = TaskState.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error

    def mark_cancelled(self) -> None:
        """Update state to cancelled."""
        self.state = TaskState.CANCELLED
        self.completed_at = datetime.utcnow()


class Channel(ABC):
    """Abstract base class for channel implementations (ARC_CMP_001).

    Each channel normalizes user input from its interface (Telegram, Web, etc.)
    into TaskMessage format. Responses are sent back through the same channel.
    The channel is stateless regarding business logic, permissions, or memory.
    """

    def __init__(self, channel_type: str):
        """Initialize channel.

        Args:
            channel_type: Identifier for this channel (e.g., 'telegram', 'web')
        """
        self.channel_type = channel_type

    @abstractmethod
    async def receive(self) -> TaskMessage:
        """Wait for and normalize user input from this channel.

        Returns:
            Normalized TaskMessage ready for platform processing

        Raises:
            ChannelError: If input cannot be normalized or channel is unavailable
        """

    @abstractmethod
    async def send(self, response: str, task_id: str) -> None:
        """Send response back through this channel.

        Args:
            response: Text to send to user
            task_id: Identifier of the task this response is for

        Raises:
            ChannelError: If response cannot be sent
        """

    async def send_status(self, status: TaskState, task_id: str) -> None:
        """Notify user of task status change (observable state per SYS_001).

        Default implementation sends status as text. Override for richer UI.

        Args:
            status: Current state of the task
            task_id: Identifier of the task
        """
        status_text = f"Task {task_id}: {status.value}"
        await self.send(status_text, task_id)
