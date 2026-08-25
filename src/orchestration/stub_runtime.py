"""Stub runtime port (ARC_CMP_003).

No agent execution environment has been selected yet: ADR_006 stays
`proposed` until the comparison called for by m02's первый подэтап
completes. This deterministic transitional layer satisfies the
RuntimePort contract so the orchestration loop can be built and tested
end-to-end without depending on any concrete agent SDK.
"""

from src.channels.base import TaskMessage

from .runtime_port import RuntimePort, RuntimePortError, RuntimeResult


class StubRuntimePort(RuntimePort):
    """Deterministic RuntimePort for tests and the pre-integration loop.

    Echoes the input back as output, unless a canned response, a task-level
    failure, or a simulated environment outage was registered for the
    exact input text.
    """

    def __init__(self) -> None:
        self._responses: dict[str, str] = {}
        self._failures: dict[str, str] = {}
        self._unavailable: set[str] = set()

    def register_response(self, user_input: str, response: str) -> None:
        """Return `response` the next time `user_input` is executed (testing only)."""
        self._responses[user_input] = response

    def register_failure(
        self, user_input: str, error_message: str = "stub runtime failure"
    ) -> None:
        """Make execution of `user_input` return a controlled failure (testing only)."""
        self._failures[user_input] = error_message

    def simulate_unavailable(self, user_input: str) -> None:
        """Make execution of `user_input` raise RuntimePortError (testing only).

        Distinct from `register_failure`: this simulates the environment
        itself being unreachable, not a normal task-level error.
        """
        self._unavailable.add(user_input)

    async def execute(self, message: TaskMessage) -> RuntimeResult:
        if message.user_input in self._unavailable:
            raise RuntimePortError(f"stub environment unavailable for '{message.user_input}'")
        if message.user_input in self._failures:
            return RuntimeResult(
                output="", succeeded=False, error_message=self._failures[message.user_input]
            )
        response = self._responses.get(message.user_input, f"echo: {message.user_input}")
        return RuntimeResult(output=response)
