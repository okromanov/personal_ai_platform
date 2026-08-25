"""Stub model gateway (ARC_CMP_004).

Which model provider to connect for m02 is still open: ADR_005 stays
`proposed` until the comparison called for by m02's четвёртый подэтап
completes and the owner accepts a candidate. This deterministic
transitional implementation satisfies the ModelGateway contract so the
orchestration loop can call a model end-to-end without depending on any
concrete provider SDK, credentials, or network access.
"""

from .base import ModelGateway, ModelGatewayError, ModelRequest, ModelResponse, ModelUsage


class StubModelGateway(ModelGateway):
    """Deterministic ModelGateway for tests and the pre-integration loop.

    Echoes the prompt back as output, unless a canned response, a
    controlled failure, or a simulated outage was registered for the
    exact prompt text.
    """

    def __init__(self) -> None:
        self._responses: dict[str, str] = {}
        self._failures: dict[str, str] = {}
        self._unavailable: set[str] = set()

    def register_response(self, prompt: str, response: str) -> None:
        """Return `response` the next time `prompt` is completed (testing only)."""
        self._responses[prompt] = response

    def register_failure(self, prompt: str, error_message: str = "stub model failure") -> None:
        """Make completion of `prompt` return a controlled failure (testing only)."""
        self._failures[prompt] = error_message

    def simulate_unavailable(self, prompt: str) -> None:
        """Make completion of `prompt` raise ModelGatewayError (testing only).

        Distinct from `register_failure`: this simulates the provider
        itself being unreachable, not a normal per-call error.
        """
        self._unavailable.add(prompt)

    async def complete(self, request: ModelRequest) -> ModelResponse:
        if request.prompt in self._unavailable:
            raise ModelGatewayError(f"stub model provider unavailable for '{request.prompt}'")
        if request.prompt in self._failures:
            return ModelResponse(
                text="", succeeded=False, error_message=self._failures[request.prompt]
            )
        response = self._responses.get(request.prompt, f"echo: {request.prompt}")
        usage = ModelUsage(
            input_tokens=len(request.prompt.split()), output_tokens=len(response.split())
        )
        return ModelResponse(text=response, usage=usage)
