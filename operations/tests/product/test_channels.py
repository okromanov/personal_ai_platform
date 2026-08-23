"""Unit tests for the Channels component (ARC_CMP_001).

Runs under the canonical `operations/scripts/quality/run_unittests.py`
discovery, so it is part of the enforced CI gate — unlike the old
`operations/tests_implementation/verify_channels.py` script, which was
never wired into any automated check.
"""

from __future__ import annotations

import asyncio
import unittest

from src.channels import ChannelError, TaskMessage, TaskState, TelegramChannel


class TelegramChannelInitTests(unittest.TestCase):
    def test_channel_type_is_telegram(self) -> None:
        channel = TelegramChannel(bot_token="test_token")
        self.assertEqual(channel.channel_type, "telegram")

    def test_default_token_is_empty(self) -> None:
        channel = TelegramChannel()
        self.assertEqual(channel.bot_token, "")


class TelegramChannelAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_receive_without_token_raises_channel_error(self) -> None:
        channel = TelegramChannel()
        with self.assertRaises(ChannelError):
            await asyncio.wait_for(channel.receive(), timeout=0.1)

    async def test_inject_and_receive_round_trips_message(self) -> None:
        channel = TelegramChannel(bot_token="test_token")
        injected = await channel.inject_message("Hello assistant", user_id="user123")

        self.assertEqual(injected.channel_type, "telegram")
        self.assertEqual(injected.user_input, "Hello assistant")
        self.assertEqual(injected.metadata["telegram_user_id"], "user123")

        received = await asyncio.wait_for(channel.receive(), timeout=1.0)
        self.assertEqual(received.user_input, "Hello assistant")
        self.assertIs(received, injected)

    async def test_send_without_token_raises_channel_error(self) -> None:
        channel = TelegramChannel()
        with self.assertRaises(ChannelError):
            await channel.send("hi", "task_1")

    async def test_send_stores_response_for_task(self) -> None:
        channel = TelegramChannel(bot_token="test_token")
        await channel.send("Here is your result", "task_001")
        self.assertEqual(channel.get_response("task_001"), "Here is your result")

    async def test_get_response_is_none_before_send(self) -> None:
        channel = TelegramChannel(bot_token="test_token")
        self.assertIsNone(channel.get_response("never_sent"))

    async def test_send_status_formats_state_into_response(self) -> None:
        channel = TelegramChannel(bot_token="test_token")
        await channel.send_status(TaskState.COMPLETED, "task_status_test")
        response = channel.get_response("task_status_test")
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("completed", response.lower())

    async def test_messages_are_received_in_fifo_order(self) -> None:
        channel = TelegramChannel(bot_token="test_token")
        await channel.inject_message("First message", user_id="user1")
        await channel.inject_message("Second message", user_id="user2")

        first = await asyncio.wait_for(channel.receive(), timeout=1.0)
        second = await asyncio.wait_for(channel.receive(), timeout=1.0)
        self.assertEqual(first.user_input, "First message")
        self.assertEqual(second.user_input, "Second message")

    async def test_reset_clears_responses_and_queue(self) -> None:
        channel = TelegramChannel(bot_token="test_token")
        await channel.inject_message("message", user_id="user1")
        await channel.send("response", "task_1")
        self.assertEqual(channel.get_response("task_1"), "response")
        self.assertFalse(channel._message_queue.empty())

        channel.reset()

        self.assertIsNone(channel.get_response("task_1"))
        self.assertTrue(channel._message_queue.empty())


class TaskMessageStateTests(unittest.TestCase):
    def test_starts_pending(self) -> None:
        msg = TaskMessage(channel_type="telegram", user_input="test")
        self.assertEqual(msg.state, TaskState.PENDING)
        self.assertIsNone(msg.completed_at)

    def test_mark_running_sets_running_state(self) -> None:
        msg = TaskMessage(channel_type="telegram", user_input="test")
        msg.mark_running()
        self.assertEqual(msg.state, TaskState.RUNNING)

    def test_mark_completed_sets_state_and_timestamp(self) -> None:
        msg = TaskMessage(channel_type="telegram", user_input="test")
        msg.mark_completed()
        self.assertEqual(msg.state, TaskState.COMPLETED)
        self.assertIsNotNone(msg.completed_at)

    def test_mark_failed_records_error_message(self) -> None:
        msg = TaskMessage(channel_type="telegram", user_input="test")
        msg.mark_failed("Test error")
        self.assertEqual(msg.state, TaskState.FAILED)
        self.assertEqual(msg.error_message, "Test error")
        self.assertIsNotNone(msg.completed_at)

    def test_mark_cancelled_sets_state_and_timestamp(self) -> None:
        msg = TaskMessage(channel_type="telegram", user_input="test")
        msg.mark_cancelled()
        self.assertEqual(msg.state, TaskState.CANCELLED)
        self.assertIsNotNone(msg.completed_at)

    def test_each_message_gets_a_unique_task_id(self) -> None:
        first = TaskMessage(channel_type="telegram", user_input="a")
        second = TaskMessage(channel_type="telegram", user_input="b")
        self.assertNotEqual(first.task_id, second.task_id)


if __name__ == "__main__":
    unittest.main()
