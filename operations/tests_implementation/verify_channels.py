#!/usr/bin/env python3.13
"""Verification script for ARC_CMP_001 channel implementation.

Runs tests without external dependencies, creates evidence record.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.channels import ChannelError, TaskState, TelegramChannel


class TestResult:
    """Track test results."""

    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def add_pass(self, test_name):
        self.tests_run += 1
        self.tests_passed += 1
        print(f"✓ {test_name}")

    def add_fail(self, test_name, error):
        self.tests_run += 1
        self.tests_failed += 1
        self.failures.append((test_name, error))
        print(f"✗ {test_name}: {error}")

    def summary(self):
        return f"Ran {self.tests_run}, passed {self.tests_passed}, failed {self.tests_failed}"


async def run_tests() -> TestResult:
    """Run all channel tests."""
    result = TestResult()

    # Test 1: Channel initialization
    try:
        channel = TelegramChannel(bot_token="test_token")
        assert channel.channel_type == "telegram"
        result.add_pass("telegram_channel_init")
    except Exception as e:
        result.add_fail("telegram_channel_init", str(e))

    # Test 2: Receive without token
    try:
        channel = TelegramChannel()  # No token
        try:
            await asyncio.wait_for(channel.receive(), timeout=0.1)
            result.add_fail("receive_without_token", "Should raise ChannelError")
        except ChannelError:
            result.add_pass("receive_without_token")
    except Exception as e:
        result.add_fail("receive_without_token", str(e))

    # Test 3: Inject and receive message
    try:
        channel = TelegramChannel(bot_token="test_token")
        msg = await channel.inject_message("Hello assistant", user_id="user123")
        assert msg.channel_type == "telegram"
        assert msg.user_input == "Hello assistant"
        assert msg.metadata["telegram_user_id"] == "user123"

        received = await asyncio.wait_for(channel.receive(), timeout=1.0)
        assert received.user_input == "Hello assistant"
        result.add_pass("inject_and_receive_message")
    except Exception as e:
        result.add_fail("inject_and_receive_message", str(e))

    # Test 4: Send response
    try:
        channel = TelegramChannel(bot_token="test_token")
        task_id = "task_001"
        response_text = "Here is your result"
        await channel.send(response_text, task_id)
        stored = channel.get_response(task_id)
        assert stored == response_text
        result.add_pass("send_response")
    except Exception as e:
        result.add_fail("send_response", str(e))

    # Test 5: Task state transitions
    try:
        from src.channels import TaskMessage

        msg = TaskMessage(channel_type="telegram", user_input="test")
        assert msg.state == TaskState.PENDING
        msg.mark_running()
        assert msg.state == TaskState.RUNNING
        msg.mark_completed()
        assert msg.state == TaskState.COMPLETED
        assert msg.completed_at is not None

        msg2 = TaskMessage(channel_type="telegram", user_input="test2")
        msg2.mark_failed("Test error")
        assert msg2.state == TaskState.FAILED
        assert msg2.error_message == "Test error"

        msg3 = TaskMessage(channel_type="telegram", user_input="test3")
        msg3.mark_cancelled()
        assert msg3.state == TaskState.CANCELLED
        result.add_pass("task_message_state_transitions")
    except Exception as e:
        result.add_fail("task_message_state_transitions", str(e))

    # Test 6: Send status
    try:
        channel = TelegramChannel(bot_token="test_token")
        task_id = "task_status_test"
        await channel.send_status(TaskState.COMPLETED, task_id)
        response = channel.get_response(task_id)
        assert response is not None, "Response should not be None"
        assert "completed" in response.lower(), (
            f"Response should contain 'completed', got: {response}"
        )
        result.add_pass("send_status")
    except Exception as e:
        result.add_fail("send_status", f"{type(e).__name__}: {str(e)}")

    # Test 7: Multiple messages
    try:
        channel = TelegramChannel(bot_token="test_token")
        await channel.inject_message("First message", user_id="user1")
        await channel.inject_message("Second message", user_id="user2")

        received1 = await asyncio.wait_for(channel.receive(), timeout=1.0)
        assert received1.user_input == "First message"

        received2 = await asyncio.wait_for(channel.receive(), timeout=1.0)
        assert received2.user_input == "Second message"
        result.add_pass("multiple_messages")
    except Exception as e:
        result.add_fail("multiple_messages", str(e))

    # Test 8: Channel reset
    try:
        channel = TelegramChannel(bot_token="test_token")
        await channel.inject_message("message", user_id="user1")
        await channel.send("response", "task_1")
        assert channel.get_response("task_1") == "response"

        channel.reset()
        assert channel.get_response("task_1") is None

        try:
            await asyncio.wait_for(channel.receive(), timeout=0.01)
            result.add_fail("channel_reset", "Queue should be empty")
        except asyncio.TimeoutError:
            result.add_pass("channel_reset")
    except Exception as e:
        result.add_fail("channel_reset", str(e))

    return result


async def main():
    """Run verification and generate report."""
    print("=" * 60)
    print("ARC_CMP_001 Channel Implementation Verification")
    print("=" * 60)
    print()

    result = await run_tests()

    print()
    print("=" * 60)
    print(result.summary())
    print("=" * 60)

    if result.tests_failed > 0:
        print("\nFailures:")
        for test_name, error in result.failures:
            print(f"  {test_name}: {error}")
        return 1
    else:
        print("\nAll tests passed ✓")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
