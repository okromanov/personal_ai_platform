"""Environment-backed secret provider for the minimal m02 deployment."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

from .base import SecretNotFoundError, SecretProvider

_LOGICAL_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


class EnvSecretProvider(SecretProvider):
    """Read secrets from a supplied environment mapping without logging values."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = os.environ if environment is None else environment

    def get(self, name: str) -> str:
        """Return a non-empty value for a logical environment name."""
        if not _LOGICAL_NAME.fullmatch(name):
            raise ValueError("Secret name must use uppercase letters, digits, and underscores")

        value = self._environment.get(name)
        if not value:
            raise SecretNotFoundError(f"Secret '{name}' is not configured")
        return value
