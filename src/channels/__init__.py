"""Channel abstraction layer for multi-interface platform.

Normalizes user input and output for supported interfaces without owning
business logic, persistent memory, or tool permissions.

This module implements ARC_CMP_001 — Каналы (Channels).
"""

from .base import Channel, ChannelError, TaskMessage, TaskState
from .telegram import TelegramChannel

__all__ = [
    "Channel",
    "ChannelError",
    "TaskMessage",
    "TaskState",
    "TelegramChannel",
]
