"""RuntimePort adapter backed by a ModelGateway (ARC_CMP_003 x ARC_CMP_004).

Demonstrates that the Orchestrator's RuntimePort boundary (TASK_003) can be
satisfied by calling a language model through ModelGateway (TASK_004)
instead of the echo-only StubRuntimePort -- without any change to the
orchestrator, channel, or owner-control code above the boundary (SYS_003).
"""

from src.channels.base import TaskMessage
from src.observability.task_events import (
    TaskEventResult,
    TaskEventSink,
    TaskEventType,
    emit_task_event,
)
from src.orchestration.runtime_port import RuntimePort, RuntimePortError, RuntimeResult

from .base import ModelGateway, ModelGatewayError, ModelRequest


class ModelBackedRuntimePort(RuntimePort):
    """RuntimePort implementation that executes a task by calling a ModelGateway."""

    def __init__(
        self, model_gateway: ModelGateway, event_sink: TaskEventSink | None = None
    ) -> None:
        self._model_gateway = model_gateway
        self._event_sink = event_sink

    def _emit(
        self,
        message: TaskMessage,
        event_type: TaskEventType,
        operation: str,
        result: TaskEventResult,
        *,
        attributes: dict[str, int] | None = None,
    ) -> None:
        emit_task_event(
            self._event_sink,
            runtime_task_id=message.runtime_task_id,
            event_type=event_type,
            component="model_gateway",
            operation=operation,
            result=result,
            attributes=attributes,
        )

    async def execute(self, message: TaskMessage) -> RuntimeResult:
        try:
            response = await self._model_gateway.complete(
                ModelRequest(
                    prompt=message.user_input,
                    runtime_task_id=message.runtime_task_id,
                )
            )
        except ModelGatewayError as exc:
            self._emit(
                message,
                TaskEventType.MODEL_CALL,
                "complete",
                TaskEventResult.FAILED,
            )
            self._emit(
                message,
                TaskEventType.ERROR,
                "model_unavailable",
                TaskEventResult.FAILED,
            )
            raise RuntimePortError("model gateway unavailable") from exc
        if not response.succeeded:
            self._emit(
                message,
                TaskEventType.MODEL_CALL,
                "complete",
                TaskEventResult.FAILED,
            )
            return RuntimeResult(output="", succeeded=False, error_message=response.error_message)
        usage = response.usage
        attributes = (
            {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}
            if usage is not None
            else None
        )
        self._emit(
            message,
            TaskEventType.MODEL_CALL,
            "complete",
            TaskEventResult.SUCCEEDED,
            attributes=attributes,
        )
        return RuntimeResult(output=response.text)
