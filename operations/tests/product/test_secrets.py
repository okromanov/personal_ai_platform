"""Product tests for INF_CMP_003 secret storage."""

from __future__ import annotations

import unittest

from src.channels import TelegramChannel
from src.secrets import EnvSecretProvider, SecretNotFoundError


class EnvSecretProviderTests(unittest.TestCase):
    def test_returns_value_for_logical_name(self) -> None:
        provider = EnvSecretProvider({"TELEGRAM_BOT_TOKEN": "test-only-token"})
        self.assertEqual(provider.get("TELEGRAM_BOT_TOKEN"), "test-only-token")

    def test_missing_secret_does_not_disclose_value(self) -> None:
        provider = EnvSecretProvider({})
        with self.assertRaises(SecretNotFoundError) as raised:
            provider.get("MODEL_API_KEY")

        message = str(raised.exception)
        self.assertIn("MODEL_API_KEY", message)
        self.assertNotIn("test-only-token", message)

    def test_empty_secret_is_not_accepted(self) -> None:
        provider = EnvSecretProvider({"MODEL_API_KEY": ""})
        with self.assertRaises(SecretNotFoundError):
            provider.get("MODEL_API_KEY")

    def test_logical_name_must_be_uppercase_environment_name(self) -> None:
        provider = EnvSecretProvider({"MODEL_API_KEY": "test-only-token"})
        with self.assertRaises(ValueError):
            provider.get("model-api-key")


class TelegramSecretIntegrationTests(unittest.TestCase):
    def test_channel_obtains_token_from_secret_provider(self) -> None:
        provider = EnvSecretProvider({"TELEGRAM_BOT_TOKEN": "test-only-token"})
        channel = TelegramChannel(secret_provider=provider)

        self.assertEqual(channel.bot_token, "test-only-token")

    def test_channel_rejects_ambiguous_token_configuration(self) -> None:
        provider = EnvSecretProvider({"TELEGRAM_BOT_TOKEN": "test-only-token"})
        with self.assertRaises(ValueError):
            TelegramChannel(bot_token="test-only-token", secret_provider=provider)


if __name__ == "__main__":
    unittest.main()
