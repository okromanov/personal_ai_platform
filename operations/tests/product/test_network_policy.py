import unittest

from network_policy import (
    CURRENT_NETWORK_POLICY,
    EgressRule,
    IngressRule,
    NetworkPolicy,
    RouteKind,
)


class NetworkPolicyTests(unittest.TestCase):
    def test_baseline_denies_ingress_egress_and_dns(self):
        self.assertFalse(CURRENT_NETWORK_POLICY.allows_ingress("api", 443))
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

    def test_ingress_requires_exact_service_and_port(self):
        policy = NetworkPolicy(ingress_rules=(IngressRule("api", 443),))
        self.assertTrue(policy.allows_ingress("api", 443))
        self.assertFalse(policy.allows_ingress("worker", 443))
        self.assertFalse(policy.allows_ingress("api", 8443))

    def test_direct_egress_requires_exact_service_target_and_port(self):
        policy = NetworkPolicy(
            egress_rules=(
                EgressRule("model", "api.example.test", 443, RouteKind.DIRECT),
            )
        )
        self.assertTrue(
            policy.allows_egress("model", "api.example.test", 443, tunnel_active=False)
        )
        self.assertFalse(
            policy.allows_egress(
                "research", "api.example.test", 443, tunnel_active=False
            )
        )
        self.assertFalse(
            policy.allows_egress(
                "model", "other.example.test", 443, tunnel_active=False
            )
        )
        self.assertFalse(
            policy.allows_egress("model", "api.example.test", 8443, tunnel_active=False)
        )

    def test_secure_tunnel_has_no_direct_fallback(self):
        policy = NetworkPolicy(
            egress_rules=(
                EgressRule(
                    "telegram", "api.telegram.org", 443, RouteKind.SECURE_TUNNEL
                ),
            )
        )
        self.assertFalse(
            policy.allows_egress(
                "telegram", "api.telegram.org", 443, tunnel_active=False
            )
        )
        self.assertTrue(
            policy.allows_egress(
                "telegram", "api.telegram.org", 443, tunnel_active=True
            )
        )

    def test_dns_requires_declared_resolver_and_egress_rule(self):
        policy = NetworkPolicy(
            egress_rules=(
                EgressRule(
                    "dns", "resolver.example.test", 853, RouteKind.SECURE_TUNNEL
                ),
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
            policy.allows_dns("other.example.test", 853, tunnel_active=True)
        )

    def test_rejects_resolver_without_dns_egress(self):
        with self.assertRaisesRegex(ValueError, "explicit dns egress rule"):
            NetworkPolicy(dns_resolvers=(("resolver.example.test", 53),))

    def test_rejects_duplicate_rules(self):
        with self.assertRaisesRegex(ValueError, "ingress rules must be unique"):
            NetworkPolicy(
                ingress_rules=(IngressRule("api", 443), IngressRule("api", 443))
            )
        rule = EgressRule("model", "api.example.test", 443, RouteKind.DIRECT)
        with self.assertRaisesRegex(ValueError, "egress rules must be unique"):
            NetworkPolicy(egress_rules=(rule, rule))

    def test_rejects_invalid_rule_data(self):
        with self.assertRaisesRegex(ValueError, "service_id"):
            IngressRule("", 443)
        with self.assertRaisesRegex(ValueError, "range 1..65535"):
            EgressRule("api", "api.example.test", 0, RouteKind.DIRECT)
        with self.assertRaisesRegex(TypeError, "RouteKind"):
            EgressRule("api", "api.example.test", 443, "direct")


if __name__ == "__main__":
    unittest.main()
