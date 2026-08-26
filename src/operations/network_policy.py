"""Fail-closed network policy for the current infrastructure baseline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RouteKind(StrEnum):
    DIRECT = "direct"
    SECURE_TUNNEL = "secure_tunnel"


@dataclass(frozen=True)
class IngressRule:
    service_id: str
    port: int

    def __post_init__(self) -> None:
        _validate_service_id(self.service_id)
        _validate_port(self.port)


@dataclass(frozen=True)
class EgressRule:
    service_id: str
    target: str
    port: int
    route: RouteKind

    def __post_init__(self) -> None:
        _validate_service_id(self.service_id)
        if not self.target.strip():
            raise ValueError("egress target must not be empty")
        _validate_port(self.port)
        if not isinstance(self.route, RouteKind):
            raise TypeError("route must be a RouteKind")


@dataclass(frozen=True)
class NetworkPolicy:
    ingress_rules: tuple[IngressRule, ...] = ()
    egress_rules: tuple[EgressRule, ...] = ()
    dns_resolvers: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        ingress_keys = {(rule.service_id, rule.port) for rule in self.ingress_rules}
        if len(ingress_keys) != len(self.ingress_rules):
            raise ValueError("ingress rules must be unique by service and port")
        egress_keys = {
            (rule.service_id, rule.target, rule.port) for rule in self.egress_rules
        }
        if len(egress_keys) != len(self.egress_rules):
            raise ValueError("egress rules must be unique by service, target and port")
        for target, port in self.dns_resolvers:
            if not any(
                rule.service_id == "dns" and rule.target == target and rule.port == port
                for rule in self.egress_rules
            ):
                raise ValueError(
                    "each DNS resolver must have an explicit dns egress rule"
                )

    def allows_ingress(self, service_id: str, port: int) -> bool:
        return any(
            rule.service_id == service_id and rule.port == port
            for rule in self.ingress_rules
        )

    def allows_egress(
        self, service_id: str, target: str, port: int, *, tunnel_active: bool
    ) -> bool:
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
        return (target, port) in self.dns_resolvers and self.allows_egress(
            "dns", target, port, tunnel_active=tunnel_active
        )


def _validate_service_id(service_id: str) -> None:
    if not service_id.strip():
        raise ValueError("service_id must not be empty")


def _validate_port(port: int) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("port must be in range 1..65535")


CURRENT_NETWORK_POLICY = NetworkPolicy()
