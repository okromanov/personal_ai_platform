"""Golden-case eval harness for the model gateway (AUD-020, ARC_CMP_004).

Runs a fixed set of prompts (operations/eval/golden_cases.json) through a
ModelGateway implementation and checks each response against declared
expectations. This is deliberately provider-agnostic, per the same
boundary ADR_003/SYS_004 already establish for the gateway itself: with
StubModelGateway (the default profile, and the only registered implementation
until TASK_015 lands a real provider) this only proves the harness and the
gateway's request/response plumbing work end-to-end -- it cannot and does
not claim to measure real response quality. TASK_015 must explicitly register
a real profile and replace stub-specific expectations before its output can
be used as model-quality evidence.

Usage:
    python3 -m operations.scripts.eval.run_eval_suite
    python3 -m operations.scripts.eval.run_eval_suite --profile stub
    python3 -m operations.scripts.eval.run_eval_suite --cases path/to/other_cases.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.models import ModelGateway, ModelGatewayError, ModelRequest, StubModelGateway

DEFAULT_CASES_PATH = Path("operations/eval/golden_cases.json")
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class GoldenCaseError(ValueError):
    """Raised when the golden-cases file itself is malformed."""


@dataclass(frozen=True)
class Check:
    check_type: str
    value: object = None

    def evaluate(self, *, text: str, succeeded: bool, duration_ms: float) -> str | None:
        """Return None if the check passes, or a failure message."""
        if self.check_type == "succeeded":
            return None if succeeded else "response did not succeed"
        if self.check_type == "non_empty":
            return None if text else "response text is empty"
        if self.check_type == "contains":
            return None if str(self.value) in text else f"response does not contain {self.value!r}"
        if self.check_type == "not_contains":
            return (
                None
                if str(self.value) not in text
                else f"response unexpectedly contains {self.value!r}"
            )
        if self.check_type == "min_length":
            return (
                None
                if len(text) >= int(str(self.value))
                else f"response length {len(text)} is below minimum {self.value}"
            )
        if self.check_type == "max_duration_ms":
            return (
                None
                if duration_ms <= float(str(self.value))
                else f"response took {duration_ms:.0f}ms, over budget {self.value}ms"
            )
        raise GoldenCaseError(f"unknown check type: {self.check_type}")


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    title: str
    prompt: str
    checks: tuple[Check, ...] = field(default_factory=tuple)
    expected_response: str | None = None


@dataclass(frozen=True)
class CaseResult:
    case: GoldenCase
    response_text: str
    succeeded: bool
    duration_ms: float
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass(frozen=True)
class EvalSuiteResult:
    results: tuple[CaseResult, ...]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.results)


GatewayFactory = Callable[[list[GoldenCase]], ModelGateway]


def load_golden_cases(path: Path) -> list[GoldenCase]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GoldenCaseError(f"cannot read golden cases from {path}: {exc}") from exc
    cases_raw = raw.get("cases") if isinstance(raw, dict) else None
    if not isinstance(cases_raw, list) or not cases_raw:
        raise GoldenCaseError(f"{path}: 'cases' must be a non-empty list")
    cases: list[GoldenCase] = []
    for entry in cases_raw:
        if not isinstance(entry, dict):
            raise GoldenCaseError(f"{path}: each case must be an object")
        checks_raw = entry.get("checks", [])
        if not isinstance(checks_raw, list):
            raise GoldenCaseError(f"{entry.get('id', '?')}: checks must be a list")
        checks = tuple(
            Check(check_type=str(item["type"]), value=item.get("value"))
            for item in checks_raw
            if isinstance(item, dict) and "type" in item
        )
        cases.append(
            GoldenCase(
                case_id=str(entry.get("id", "")).strip() or "UNKNOWN",
                title=str(entry.get("title", "")),
                prompt=str(entry.get("prompt", "")),
                checks=checks,
                expected_response=(
                    str(entry["expected_response"]) if "expected_response" in entry else None
                ),
            )
        )
    return cases


async def run_case(gateway: ModelGateway, case: GoldenCase) -> CaseResult:
    start = time.monotonic()
    response = await gateway.complete(ModelRequest(prompt=case.prompt))
    duration_ms = (time.monotonic() - start) * 1000
    failures = tuple(
        message
        for check in case.checks
        if (
            message := check.evaluate(
                text=response.text, succeeded=response.succeeded, duration_ms=duration_ms
            )
        )
        is not None
    )
    return CaseResult(
        case=case,
        response_text=response.text,
        succeeded=response.succeeded,
        duration_ms=duration_ms,
        failures=failures,
    )


async def run_eval_suite(gateway: ModelGateway, cases: list[GoldenCase]) -> EvalSuiteResult:
    results = []
    for case in cases:
        results.append(await run_case(gateway, case))
    return EvalSuiteResult(results=tuple(results))


def _default_gateway(cases: list[GoldenCase]) -> ModelGateway:
    gateway = StubModelGateway()
    for case in cases:
        if case.expected_response is not None:
            gateway.register_response(case.prompt, case.expected_response)
    return gateway


def build_gateway(
    profile: str,
    cases: list[GoldenCase],
    factories: dict[str, GatewayFactory] | None = None,
) -> ModelGateway:
    available: dict[str, GatewayFactory] = {"stub": _default_gateway}
    available.update(factories or {})
    factory = available.get(profile)
    if factory is None:
        names = ", ".join(sorted(available)) or "none"
        raise GoldenCaseError(f"unknown eval profile {profile!r}; available profiles: {names}")
    return factory(cases)


def _print_report(
    result: EvalSuiteResult,
    *,
    profile: str,
    git_sha: str | None,
) -> None:
    print(f"profile: {profile}")
    print(f"git_sha: {git_sha or 'unbound'}")
    for case_result in result.results:
        status = "PASS" if case_result.passed else "FAIL"
        print(f"[{status}] {case_result.case.case_id} — {case_result.case.title}")
        for failure in case_result.failures:
            print(f"       {failure}")
    passed = sum(1 for r in result.results if r.passed)
    print(f"\n{passed}/{len(result.results)} golden cases passed.")


def main(
    argv: Sequence[str] | None = None,
    *,
    gateway_factories: dict[str, GatewayFactory] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--profile", default="stub")
    parser.add_argument("--git-sha")
    args = parser.parse_args(argv)

    try:
        cases = load_golden_cases(args.cases)
        if args.profile != "stub" and not FULL_SHA_PATTERN.fullmatch(args.git_sha or ""):
            raise GoldenCaseError("non-stub eval profile requires --git-sha with a full 40-hex SHA")
        gateway = build_gateway(args.profile, cases, gateway_factories)
        result = asyncio.run(run_eval_suite(gateway, cases))
    except GoldenCaseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ModelGatewayError as exc:
        print(f"ERROR: model gateway unavailable: {exc}", file=sys.stderr)
        return 1

    _print_report(result, profile=args.profile, git_sha=args.git_sha)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
