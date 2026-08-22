"""Telegram channel implementation (ARC_CMP_001).

Normalizes Telegram messages into TaskMessage format per SYS_001.
Handles single interface with stateless message normalization.
"""

import asyncio
from typing import Any, Optional

from .base import Channel, ChannelError, TaskMessage, TaskState


class TelegramChannel(Channel):
    """Telegram channel for normalized task input/output.

    Implements the minimal Telegram interface required for m02:
    - Accept text messages from Telegram
    - Normalize to TaskMessage
    - Send responses back through Telegram
    - Provide observable task state

    This is a minimal implementation for the m02 scenario.
    Production would integrate with python-telegram-bot library.
    """

    def __init__(self, bot_token: str = ""):
        """Initialize Telegram channel.

        Args:
            bot_token: Telegram bot token (from environment or config in production)
        """
        super().__init__("telegram")
        self.bot_token = bot_token
        self._message_queue: asyncio.Queue[TaskMessage] = asyncio.Queue()
        self._responses: dict[str, str] = {}

    async def receive(self) -> TaskMessage:
        """Wait for and normalize Telegram message.

        In production, would connect to Telegram Bot API via webhook or polling.
        For m02 testing, uses in-memory queue to simulate incoming messages.

        Returns:
            Normalized TaskMessage from Telegram input

        Raises:
            ChannelError: If bot is not configured or message is invalid
        """
        if not self.bot_token:
            raise ChannelError("Telegram bot token not configured")

        try:
            # In production, this would wait for real Telegram updates
            # For m02, we simulate with queue
            message = await asyncio.wait_for(self._message_queue.get(), timeout=30.0)
            return message
        except asyncio.TimeoutError:
            raise ChannelError("No message received from Telegram within timeout")

    async def send(self, response: str, task_id: str) -> None:
        """Send response through Telegram channel.

        In production, would call Telegram Bot API to send message.
        For m02, stores response in memory for verification.

        Args:
            response: Text to send to user
            task_id: Identifier of the task this response is for

        Raises:
            ChannelError: If send fails
        """
        if not self.bot_token:
            raise ChannelError("Telegram bot token not configured")

        # Store for testing/verification
        self._responses[task_id] = response
        # In production: await send_message_via_telegram_api(chat_id, response)

    async def inject_message(self, text: str, user_id: str = "test_user") -> TaskMessage:
        """Inject a test message into the channel queue (for testing only).

        Args:
            text: Message text
            user_id: Telegram user ID

        Returns:
            The TaskMessage that was queued
        """
        msg = TaskMessage(
            channel_type=self.channel_type,
            user_input=text,
            metadata={
                "telegram_user_id": user_id,
                "telegram_chat_id": f"chat_{user_id}",
            },
        )
        await self._message_queue.put(msg)
        return msg

    def get_response(self, task_id: str) -> Optional[str]:
        """Retrieve sent response for verification (testing only).

        Args:
            task_id: Task identifier

        Returns:
            Response text if sent, None otherwise
        """
        return self._responses.get(task_id)

    def reset(self) -> None:
        """Clear internal state (testing only)."""
        self._responses.clear()
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
