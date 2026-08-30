"""Tests for the golden-case eval harness (AUD-020)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from operations.scripts.eval.run_eval_suite import (
    Check,
    GoldenCase,
    GoldenCaseError,
    _default_gateway,
    build_gateway,
    load_golden_cases,
    main,
    run_case,
    run_eval_suite,
)
from src.models import (
    ModelGateway,
    ModelGatewayError,
    ModelRequest,
    ModelResponse,
    StubModelGateway,
)


class CheckTests(unittest.TestCase):
    def test_succeeded_check(self) -> None:
        check = Check(check_type="succeeded")
        self.assertIsNone(check.evaluate(text="x", succeeded=True, duration_ms=0))
        self.assertIsNotNone(check.evaluate(text="x", succeeded=False, duration_ms=0))

    def test_non_empty_check(self) -> None:
        check = Check(check_type="non_empty")
        self.assertIsNone(check.evaluate(text="hello", succeeded=True, duration_ms=0))
        self.assertIsNotNone(check.evaluate(text="", succeeded=True, duration_ms=0))

    def test_contains_and_not_contains_checks(self) -> None:
        contains = Check(check_type="contains", value="foo")
        self.assertIsNone(contains.evaluate(text="a foo b", succeeded=True, duration_ms=0))
        self.assertIsNotNone(contains.evaluate(text="a bar b", succeeded=True, duration_ms=0))

        not_contains = Check(check_type="not_contains", value="foo")
        self.assertIsNone(not_contains.evaluate(text="a bar b", succeeded=True, duration_ms=0))
        self.assertIsNotNone(not_contains.evaluate(text="a foo b", succeeded=True, duration_ms=0))

    def test_min_length_check(self) -> None:
        check = Check(check_type="min_length", value=5)
        self.assertIsNone(check.evaluate(text="12345", succeeded=True, duration_ms=0))
        self.assertIsNotNone(check.evaluate(text="1234", succeeded=True, duration_ms=0))

    def test_max_duration_ms_check(self) -> None:
        check = Check(check_type="max_duration_ms", value=100)
        self.assertIsNone(check.evaluate(text="x", succeeded=True, duration_ms=50))
        self.assertIsNotNone(check.evaluate(text="x", succeeded=True, duration_ms=150))

    def test_unknown_check_type_raises(self) -> None:
        check = Check(check_type="not_a_real_check")
        with self.assertRaises(GoldenCaseError):
            check.evaluate(text="x", succeeded=True, duration_ms=0)


class LoadGoldenCasesTests(unittest.TestCase):
    def test_loads_the_real_golden_cases_file(self) -> None:
        cases = load_golden_cases(Path("operations/eval/golden_cases.json"))
        self.assertGreaterEqual(len(cases), 1)
        self.assertTrue(all(isinstance(case, GoldenCase) for case in cases))
        self.assertTrue(all(case.checks for case in cases))

    def test_rejects_missing_file(self) -> None:
        with self.assertRaises(GoldenCaseError):
            load_golden_cases(Path("/nonexistent/golden_cases.json"))

    def test_rejects_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaises(GoldenCaseError):
                load_golden_cases(path)

    def test_rejects_missing_cases_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.json"
            path.write_text(json.dumps({"version": 1}), encoding="utf-8")
            with self.assertRaises(GoldenCaseError):
                load_golden_cases(path)

    def test_parses_expected_response_and_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.json"
            path.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "id": "EVAL_X",
                                "title": "example",
                                "prompt": "hi",
                                "expected_response": "hello there",
                                "checks": [{"type": "contains", "value": "hello"}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            cases = load_golden_cases(path)
            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0].expected_response, "hello there")
            self.assertEqual(cases[0].checks[0].check_type, "contains")


class RunEvalSuiteTests(unittest.IsolatedAsyncioTestCase):
    async def test_case_with_registered_response_passes_its_checks(self) -> None:
        case = GoldenCase(
            case_id="EVAL_X",
            title="example",
            prompt="hi",
            checks=(Check(check_type="contains", value="hello"),),
            expected_response="hello there",
        )
        gateway = _default_gateway([case])
        result = await run_case(gateway, case)
        self.assertTrue(result.passed)
        self.assertEqual(result.response_text, "hello there")

    async def test_case_reports_specific_check_failures(self) -> None:
        case = GoldenCase(
            case_id="EVAL_X",
            title="example",
            prompt="hi",
            checks=(Check(check_type="contains", value="goodbye"),),
            expected_response="hello there",
        )
        gateway = _default_gateway([case])
        result = await run_case(gateway, case)
        self.assertFalse(result.passed)
        self.assertIn("goodbye", result.failures[0])

    async def test_suite_passes_only_when_every_case_passes(self) -> None:
        passing = GoldenCase(
            case_id="EVAL_A", title="a", prompt="a", checks=(Check(check_type="non_empty"),)
        )
        failing = GoldenCase(
            case_id="EVAL_B",
            title="b",
            prompt="b",
            checks=(Check(check_type="contains", value="nope"),),
        )
        gateway = _default_gateway([passing, failing])
        suite_result = await run_eval_suite(gateway, [passing, failing])
        self.assertFalse(suite_result.passed)
        self.assertTrue(suite_result.results[0].passed)
        self.assertFalse(suite_result.results[1].passed)

    async def test_provider_outage_surfaces_as_a_gateway_error_not_a_silent_pass(self) -> None:
        case = GoldenCase(
            case_id="EVAL_X", title="example", prompt="hi", checks=(Check(check_type="succeeded"),)
        )
        gateway = StubModelGateway()
        gateway.simulate_unavailable("hi")
        with self.assertRaises(ModelGatewayError):
            await run_case(gateway, case)

    async def test_real_golden_cases_pass_against_the_default_stub_gateway(self) -> None:
        cases = load_golden_cases(Path("operations/eval/golden_cases.json"))
        gateway = _default_gateway(cases)
        result = await run_eval_suite(gateway, cases)
        self.assertTrue(result.passed, [r.failures for r in result.results if not r.passed])


class EvalProfileTests(unittest.TestCase):
    class DegradedGateway(ModelGateway):
        async def complete(self, request: ModelRequest) -> ModelResponse:
            del request
            return ModelResponse(text="degraded")

    def test_unknown_profile_is_rejected(self) -> None:
        cases = load_golden_cases(Path("operations/eval/golden_cases.json"))
        with self.assertRaises(GoldenCaseError):
            build_gateway("missing", cases)

    def test_non_stub_profile_requires_full_sha(self) -> None:
        exit_code = main(
            ["--profile", "degraded"],
            gateway_factories={"degraded": lambda _cases: self.DegradedGateway()},
        )
        self.assertEqual(exit_code, 2)

    def test_canonical_entrypoint_fails_for_degraded_non_stub_profile(self) -> None:
        exit_code = main(
            ["--profile", "degraded", "--git-sha", "a" * 40],
            gateway_factories={"degraded": lambda _cases: self.DegradedGateway()},
        )
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
