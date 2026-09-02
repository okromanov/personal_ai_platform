"""Model gateway abstraction (ARC_CMP_004).

Stable, provider-agnostic boundary between the platform and a language
model. Per ADR_003, normalizes requests, responses, errors, timeouts, and
usage metrics behind one contract (SYS_004) so swapping the concrete
provider never touches the caller's code. Which provider to connect for
m02 is a separate, still open decision (ADR_005, `proposed`): this
contract itself does not name or import any provider SDK.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ModelGatewayError(Exception):
    """Raised when the provider itself cannot even be reached (outage, bad credentials)."""


@dataclass(frozen=True)
class ModelUsage:
    """Usage metrics for one model call (SYS_004).

    Attributes:
        input_tokens: Tokens consumed by the prompt.
        output_tokens: Tokens produced in the response.
    """

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class ModelRequest:
    """Normalized request to a language model.

    Attributes:
        prompt: The text to send to the model.
        timeout_seconds: Maximum time to wait for a response (SYS_004).
        runtime_task_id: Internal correlation identifier when the call belongs
            to a task execution (ADR_004).
    """

    prompt: str
    timeout_seconds: float = 30.0
    runtime_task_id: str | None = None


@dataclass(frozen=True)
class ModelResponse:
    """Normalized outcome of one model call.

    Attributes:
        text: Model output text.
        succeeded: Whether the call completed without error.
        error_message: Present when succeeded is False.
        usage: Token usage for the call, when available.
    """

    text: str
    succeeded: bool = True
    error_message: str | None = None
    usage: ModelUsage | None = None


class ModelGateway(ABC):
    """Abstract contract for a swappable language model provider.

    Implementations own the specifics of a concrete provider SDK, request
    format, and error codes. Swapping the implementation must not require
    changes to the orchestrator, channel, or task contracts above this
    boundary (SYS_004). Admissibility of the data in `prompt` for a given
    provider/model (SEC_CTL_015) is decided by the caller before this
    contract is invoked -- a gateway implementation never infers it from
    the request itself, and a fallback path must not silently raise the
    permitted data level.
    """

    @abstractmethod
    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Run one model call to completion.

        Args:
            request: Normalized model request.

        Returns:
            ModelResponse with the produced text, or a controlled failure
            (`succeeded=False`) for an expected per-call error such as a
            rejected request or a model-side failure.

        Raises:
            ModelGatewayError: If the provider itself cannot be reached at
                all (network outage, invalid credentials). Expected
                per-call failures should be returned as a failed
                ModelResponse instead of raising.
        """
