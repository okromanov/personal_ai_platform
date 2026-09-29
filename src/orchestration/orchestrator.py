"""Task orchestration loop (ARC_CMP_003).

Implements the ordinary-task flow (ARC_FLOW_001): identity and owner-rule
check -> task state -> RuntimePort -> response. Owns no secrets, owner
control state, or canonical long-lived memory directly -- both checks and
all state changes go through OwnerControl (ARC_CMP_002); the connected
RuntimePort is the only place a concrete agent environment appears.
"""

from src.channels.base import Channel, TaskMessage
from src.observability.task_events import (
    TaskEventResult,
    TaskEventSink,
    TaskEventType,
    emit_task_event,
)
from src.owner_control.base import EmergencyStopActive, IdentityRejected, OwnerControl

from .runtime_port import RuntimePort, RuntimePortError


class Orchestrator:
    """Runs one TaskMessage through the ordinary task cycle (ARC_FLOW_001)."""

    def __init__(
        self,
        owner_control: OwnerControl,
        runtime: RuntimePort,
        event_sink: TaskEventSink | None = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            owner_control: Identity and emergency-switch gate (ARC_CMP_002).
            runtime: Connected agent execution environment (ARC_CMP_003).
        """
        self._owner_control = owner_control
        self._runtime = runtime
        self._event_sink = event_sink

    def _emit(
        self,
        message: TaskMessage,
        event_type: TaskEventType,
        operation: str,
        result: TaskEventResult,
    ) -> None:
        emit_task_event(
            self._event_sink,
            runtime_task_id=message.runtime_task_id,
            event_type=event_type,
            component="orchestrator",
            operation=operation,
            result=result,
        )

    async def handle(
        self, message: TaskMessage, *, subject_id: str, channel: Channel
    ) -> TaskMessage:
        """Run the ordinary task cycle for `message` and reply through `channel`.

        `subject_id` is the channel-specific identity of the sender (e.g. a
        Telegram user id), extracted by the caller -- the orchestrator has
        no knowledge of any particular channel's metadata shape.

        Returns the same `message`, mutated to its final observable state
        (SYS_001): completed, failed, or cancelled. Never raises for a
        controlled outcome -- identity rejection, an active emergency
        switch, and a failed runtime execution are all reported back to
        the owner as a normal response, not left as a hung operation.
        """
        try:
            self._owner_control.verify_identity(subject_id)
            self._emit(
                message,
                TaskEventType.POLICY_DECISION,
                "verify_identity",
                TaskEventResult.ALLOWED,
            )
            self._owner_control.check_emergency_stop()
            self._emit(
                message,
                TaskEventType.POLICY_DECISION,
                "emergency_stop",
                TaskEventResult.ALLOWED,
            )
        except IdentityRejected:
            message.mark_cancelled()
            self._emit(
                message,
                TaskEventType.POLICY_DECISION,
                "verify_identity",
                TaskEventResult.DENIED,
            )
            self._emit(
                message,
                TaskEventType.STATE_TRANSITION,
                "pending_to_cancelled",
                TaskEventResult.CANCELLED,
            )
            await channel.send("Действие отклонено: личность не подтверждена.", message.task_id)
            return message
        except EmergencyStopActive:
            message.mark_cancelled()
            self._emit(
                message,
                TaskEventType.POLICY_DECISION,
                "emergency_stop",
                TaskEventResult.DENIED,
            )
            self._emit(
                message,
                TaskEventType.STATE_TRANSITION,
                "pending_to_cancelled",
                TaskEventResult.CANCELLED,
            )
            await channel.send("Платформа остановлена аварийным выключателем.", message.task_id)
            return message

        message.mark_running()
        self._emit(
            message,
            TaskEventType.STATE_TRANSITION,
            "pending_to_running",
            TaskEventResult.SUCCEEDED,
        )
        self._emit(
            message,
            TaskEventType.CHECKPOINT,
            "runtime_dispatch",
            TaskEventResult.RECORDED,
        )
        try:
            result = await self._runtime.execute(message)
        except RuntimePortError:
            message.mark_failed("среда выполнения недоступна")
            self._emit(
                message,
                TaskEventType.ERROR,
                "runtime_unavailable",
                TaskEventResult.FAILED,
            )
            self._emit(
                message,
                TaskEventType.STATE_TRANSITION,
                "running_to_failed",
                TaskEventResult.FAILED,
            )
            await channel.send(
                "Среда выполнения сейчас недоступна. Попробуйте ещё раз позже.", message.task_id
            )
            return message
        if result.succeeded:
            message.mark_completed()
            self._emit(
                message,
                TaskEventType.STATE_TRANSITION,
                "running_to_completed",
                TaskEventResult.SUCCEEDED,
            )
            await channel.send(result.output, message.task_id)
        else:
            error = result.error_message or "выполнение завершилось ошибкой"
            message.mark_failed(error)
            self._emit(
                message,
                TaskEventType.ERROR,
                "runtime_failed",
                TaskEventResult.FAILED,
            )
            self._emit(
                message,
                TaskEventType.STATE_TRANSITION,
                "running_to_failed",
                TaskEventResult.FAILED,
            )
            await channel.send(f"Не удалось выполнить задачу: {error}", message.task_id)
        return message
