"""Model gateway: normalized access to a language model provider.

Provides a stable contract (ModelGateway) for model requests, responses,
errors, timeouts, and usage metrics, independent of any concrete provider
SDK. Includes a deterministic transitional implementation used until a
real provider is connected (ADR_005, `proposed`) and an adapter that lets
the Orchestrator's RuntimePort boundary call a model through this contract.

This module implements ARC_CMP_004 — Шлюз моделей (Model Gateway).
"""

from .base import ModelGateway, ModelGatewayError, ModelRequest, ModelResponse, ModelUsage
from .runtime_adapter import ModelBackedRuntimePort
from .stub_gateway import StubModelGateway

__all__ = [
    "ModelBackedRuntimePort",
    "ModelGateway",
    "ModelGatewayError",
    "ModelRequest",
    "ModelResponse",
    "ModelUsage",
    "StubModelGateway",
]
