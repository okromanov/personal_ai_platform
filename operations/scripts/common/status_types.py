"""Shared TypedDict shapes for the project status/task/test data pipeline.

Several modules (`tasks/generate.py`, `status/generate_project_status.py`,
`status/human_status.py`, `tasks/check_change_scope.py`, ...) pass the same
milestone/task/test-spec dictionaries through each other. Before these types
existed every one of those functions returned `dict[str, object]`, so mypy
could not see past the boundary and every downstream `.get()`/index/iteration
was flagged as operating on `object` — the single largest source of mypy
baseline debt in the project. Typing the boundary here removes the leak at
its root instead of silencing each downstream symptom individually.
"""

from __future__ import annotations

from typing import TypedDict


class ChecklistItem(TypedDict):
    done: bool
    text: str


class TestRef(TypedDict):
    id: str
    path: str


class OwnerFollowup(TypedDict):
    status: str
    action: str


class TaskItem(TypedDict):
    id: str
    title: str
    work_state: str
    version: str
    path: str
    depends_on: list[str]
    traces_to: list[str]
    implements: list[str]
    component: str
    delivery_role: str
    allowed_paths: list[str]
    blocker: str
    tests: list[TestRef]
    next_actor: str
    owner_action: str
    owner_followups: list[OwnerFollowup]
    checklist: list[ChecklistItem]
    steps_done: int
    steps_total: int
    steps_remaining: int
    body: str


class TasksReport(TypedDict):
    count: int
    states: dict[str, int]
    tasks: list[TaskItem]


class MilestoneItem(TypedDict):
    id: str
    title: str
    work_state: str
    scope: list[str]
    result: str


class MilestonesReport(TypedDict):
    count: int
    items: list[MilestoneItem]
    current: MilestoneItem
    states: dict[str, int]


class TestSpecItem(TypedDict):
    id: str
    spec_state: str
    execution: str
    automated_evidence: str
    manual_evidence: str
    traces_to: list[str]
    verifies: list[str]
    accepts: list[str]
    title: str
    path: str


class TestSpecsReport(TypedDict):
    count: int
    items: list[TestSpecItem]
    states: dict[str, int]


class UnitSummary(TypedDict):
    ok: bool
    total: int
    passed: int
    failed: int
    duration: float | None
    label: str
    problems: list[str]
