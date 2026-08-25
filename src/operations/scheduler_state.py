"""Scheduler logical state (ARC_CMP_009).

Stores a scheduling intent and a reference to its permitted capability
(SEC_CTL_017) -- never a permanent snapshot of permission -- plus a
paused/resumed switch: a deliberately limited recovery action that stops
new runs without touching owner control, task state, or any other
component's data (no full administrative access).
"""

from dataclasses import dataclass

from src.task_state import TaskLifecycleStore


@dataclass(frozen=True)
class ScheduledIntent:
    """A registered scheduling intent: what to run, not permission to run it.

    Attributes:
        intent_id: Unique identifier for this scheduled intent.
        capability_name: The capability this intent may invoke -- resolved
            and re-authorized by the tool gateway at run time, never
            cached here as a standing permission.
        task_id: The TaskLifecycleStore-tracked task this intent is tied to.
    """

    intent_id: str
    capability_name: str
    task_id: str


class SchedulerState:
    """Logical scheduler state: registered intents and a pause switch.

    Owns no timer and no execution of its own -- running an intent still
    requires the full ordinary/tool-call checks (identity, emergency
    switch, tool authorization) at the moment it actually runs. This
    class only tracks what is registered and whether it is currently
    eligible to be considered.
    """

    def __init__(self) -> None:
        self._intents: dict[str, ScheduledIntent] = {}
        self._paused = False

    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        """Stop every intent from being considered runnable.

        A limited, reversible recovery action: it does not cancel any
        task, does not touch owner control, and grants no administrative
        access -- it only stops new scheduled runs from starting.
        """
        self._paused = True

    def resume(self) -> None:
        """Undo `pause`: intents become runnable again, subject to their own state."""
        self._paused = False

    def register_intent(self, intent: ScheduledIntent) -> None:
        """Register `intent`, replacing any previous intent with the same id."""
        self._intents[intent.intent_id] = intent

    def runnable_intents(self, store: TaskLifecycleStore) -> list[ScheduledIntent]:
        """Intents eligible to run now.

        Empty while paused. Otherwise excludes any intent whose task has
        been cancelled in `store` -- the scheduler's view stays consistent
        with individual task state (ARC_CMP_007) instead of holding a
        stale intent for a task the owner already cancelled.
        """
        if self._paused:
            return []
        return [
            intent
            for intent in self._intents.values()
            if not store.get_state(intent.task_id).cancelled
        ]
