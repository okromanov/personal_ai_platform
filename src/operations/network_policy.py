"""Fail-closed network policy for the current infrastructure baseline.

The policy is deliberately independent of a cloud firewall implementation.
At m02 the runtime has no real network integrations, so the checked-in
baseline permits neither public ingress nor external egress. A later task that
adds an integration must name its service, destination and route here before
the matching host or provider rule can be provisioned.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RouteKind(StrEnum):
    """The only routes a declared external destination may use."""

    DIRECT = "direct"
    SECURE_TUNNEL = "secure_tunnel"


@dataclass(frozen=True)
class IngressRule:
    """One explicitly exposed listener for a named platform service."""

    service_id: str
    port: int

    def __post_init__(self) -> None:
        _validate_service_id(self.service_id)
        _validate_port(self.port)


@dataclass(frozen=True)
class EgressRule:
    """One destination a named service may contact over a declared route."""

    service_id: str
    target: str
    port: int
    route: RouteKind

    def __post_init__(self) -> None:
        _validate_service_id(self.service_id)
        if not self.target.strip():
            raise ValueError("egress target must not be empty")
        _validate_port(self.port)


@dataclass(frozen=True)
class NetworkPolicy:
    """An explicit allowlist with no implicit DNS, ingress or egress route."""

    ingress_rules: tuple[IngressRule, ...] = ()
    egress_rules: tuple[EgressRule, ...] = ()
    dns_resolvers: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        ingress_keys = {(rule.service_id, rule.port) for rule in self.ingress_rules}
        if len(ingress_keys) != len(self.ingress_rules):
            raise ValueError("ingress rules must be unique by service and port")

        egress_keys = {(rule.service_id, rule.target, rule.port) for rule in self.egress_rules}
        if len(egress_keys) != len(self.egress_rules):
            raise ValueError("egress rules must be unique by service, target and port")

        for target, port in self.dns_resolvers:
            if not any(
                rule.service_id == "dns" and rule.target == target and rule.port == port
                for rule in self.egress_rules
            ):
                raise ValueError("each DNS resolver must have an explicit dns egress rule")

    def allows_ingress(self, port: int) -> bool:
        """Return whether a listener is explicitly exposed on ``port``."""
        return any(rule.port == port for rule in self.ingress_rules)

    def allows_egress(
        self, service_id: str, target: str, port: int, *, tunnel_active: bool
    ) -> bool:
        """Authorize only an exact rule; a required tunnel never falls back."""
        rule = next(
            (
                candidate
                for candidate in self.egress_rules
                if candidate.service_id == service_id
                and candidate.target == target
                and candidate.port == port
            ),
            None,
        )
        if rule is None:
            return False
        return rule.route is RouteKind.DIRECT or tunnel_active

    def allows_dns(self, target: str, port: int, *, tunnel_active: bool) -> bool:
        """Allow DNS only for a declared resolver and its declared route."""
        return (target, port) in self.dns_resolvers and self.allows_egress(
            "dns", target, port, tunnel_active=tunnel_active
        )


def _validate_service_id(service_id: str) -> None:
    if not service_id.strip():
        raise ValueError("service_id must not be empty")


def _validate_port(port: int) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("port must be in range 1..65535")


# No service in m02 is allowed to use the network until a later TASK declares
# a concrete integration and provisions the corresponding infrastructure rule.
CURRENT_NETWORK_POLICY = NetworkPolicy()
