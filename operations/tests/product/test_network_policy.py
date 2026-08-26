"""Unit tests for the fail-closed INF_CMP_002 network policy."""

from __future__ import annotations

import unittest

from src.operations.network_policy import (
    CURRENT_NETWORK_POLICY,
    EgressRule,
    IngressRule,
    NetworkPolicy,
    RouteKind,
)


class NetworkPolicyTests(unittest.TestCase):
    def test_current_baseline_exposes_no_public_ingress(self) -> None:
        self.assertFalse(CURRENT_NETWORK_POLICY.allows_ingress(80))
        self.assertFalse(CURRENT_NETWORK_POLICY.allows_ingress(443))

    def test_current_baseline_denies_egress_and_dns(self) -> None:
        self.assertFalse(
            CURRENT_NETWORK_POLICY.allows_egress(
                "model", "api.example.test", 443, tunnel_active=True
            )
        )
        self.assertFalse(
            CURRENT_NETWORK_POLICY.allows_dns(
                "resolver.example.test", 853, tunnel_active=True
            )
        )

    def test_direct_rule_requires_exact_service_target_and_port(self) -> None:
        policy = NetworkPolicy(
            egress_rules=(
                EgressRule("model", "api.example.test", 443, RouteKind.DIRECT),
            )
        )

        self.assertTrue(
            policy.allows_egress("model", "api.example.test", 443, tunnel_active=False)
        )
        self.assertFalse(
            policy.allows_egress("research", "api.example.test", 443, tunnel_active=False)
        )
        self.assertFalse(
            policy.allows_egress("model", "api.example.test", 8443, tunnel_active=False)
        )
        self.assertFalse(
            policy.allows_egress(
                "model", "other.example.test", 443, tunnel_active=False
            )
        )

    def test_secure_tunnel_rule_denies_traffic_when_the_tunnel_is_down(self) -> None:
        policy = NetworkPolicy(
            egress_rules=(
                EgressRule(
                    "telegram", "api.telegram.org", 443, RouteKind.SECURE_TUNNEL
                ),
            )
        )

        self.assertFalse(
            policy.allows_egress("telegram", "api.telegram.org", 443, tunnel_active=False)
        )
        self.assertTrue(
            policy.allows_egress("telegram", "api.telegram.org", 443, tunnel_active=True)
        )

    def test_dns_requires_a_declared_dns_rule(self) -> None:
        policy = NetworkPolicy(
            egress_rules=(
                EgressRule("dns", "resolver.example.test", 853, RouteKind.SECURE_TUNNEL),
            ),
            dns_resolvers=(("resolver.example.test", 853),),
        )

        self.assertFalse(
            policy.allows_dns("resolver.example.test", 853, tunnel_active=False)
        )
        self.assertTrue(
            policy.allows_dns("resolver.example.test", 853, tunnel_active=True)
        )
        self.assertFalse(
            policy.allows_dns("other-resolver.example.test", 853, tunnel_active=True)
        )

    def test_dns_resolver_without_dns_egress_rule_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "explicit dns egress rule"):
            NetworkPolicy(dns_resolvers=(("resolver.example.test", 53),))

    def test_duplicate_egress_rule_is_rejected(self) -> None:
        rule = EgressRule("model", "api.example.test", 443, RouteKind.DIRECT)

        with self.assertRaisesRegex(ValueError, "egress rules must be unique"):
            NetworkPolicy(egress_rules=(rule, rule))

    def test_invalid_ingress_and_egress_ports_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "range 1..65535"):
            IngressRule("api", 0)
        with self.assertRaisesRegex(ValueError, "range 1..65535"):
            EgressRule("api", "api.example.test", 65536, RouteKind.DIRECT)


if __name__ == "__main__":
    unittest.main()
