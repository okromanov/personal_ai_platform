"""Operational functions: scheduler logical state and health aggregation.

Provides the logical state a running platform needs to answer basic
operational questions -- is it healthy, what is scheduled, is a given
scheduled intent still eligible to run -- without owning any physical
infrastructure (observability storage, deployment mechanics), which
belongs to the infrastructure components instead.

This module implements ARC_CMP_009 — Эксплуатационные функции
(Operational Functions).
"""

from .health import DependencyStatus, HealthAggregator, HealthCheck, HealthReport
from .health_check import build_health_aggregator
from .scheduler_state import ScheduledIntent, SchedulerState

__all__ = [
    "DependencyStatus",
    "HealthAggregator",
    "HealthCheck",
    "HealthReport",
    "ScheduledIntent",
    "SchedulerState",
    "build_health_aggregator",
]
