"""Provider-agnostic contract for retrieving a named secret."""

from abc import ABC, abstractmethod


class SecretNotFoundError(LookupError):
    """Raised when a required logical secret is absent without disclosing its value."""


class SecretProvider(ABC):
    """Return the minimal secret value requested by a consumer."""

    @abstractmethod
    def get(self, name: str) -> str:
        """Return a secret by logical name."""
