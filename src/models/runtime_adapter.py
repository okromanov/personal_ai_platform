"""RuntimePort adapter backed by a ModelGateway (ARC_CMP_003 x ARC_CMP_004).

Demonstrates that the Orchestrator's RuntimePort boundary (TASK_003) can be
satisfied by calling a language model through ModelGateway (TASK_004)
instead of the echo-only StubRuntimePort -- without any change to the
orchestrator, channel, or owner-control code above the boundary (SYS_003).
"""

from src.channels.base import TaskMessage
from src.orchestration.runtime_port import RuntimePort, RuntimePortError, RuntimeResult

from .base import ModelGateway, ModelGatewayError, ModelRequest


class ModelBackedRuntimePort(RuntimePort):
    """RuntimePort implementation that executes a task by calling a ModelGateway."""

    def __init__(self, model_gateway: ModelGateway) -> None:
        self._model_gateway = model_gateway

    async def execute(self, message: TaskMessage) -> RuntimeResult:
        try:
            response = await self._model_gateway.complete(ModelRequest(prompt=message.user_input))
        except ModelGatewayError as exc:
            raise RuntimePortError(f"model gateway unavailable: {exc}") from exc
        if not response.succeeded:
            return RuntimeResult(output="", succeeded=False, error_message=response.error_message)
        return RuntimeResult(output=response.text)
