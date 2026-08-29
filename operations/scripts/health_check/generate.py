#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import atomic_write, find_project_root
from operations.scripts.documents.template_contracts import assert_registered_output
from operations.scripts.health_check.metrics import (
    RepositoryHealth,
    assess_health,
    collect_code_quality_metrics,
    collect_coverage_policy,
    collect_git_metrics,
    collect_test_metrics,
)
from operations.scripts.health_check.reporter import generate_report, print_summary


def main() -> int:
    """Generate repository health check report."""
    parser = argparse.ArgumentParser(
        description="Generate repository health check report",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file for report (default: runtime/health_check_report.md)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary to stdout instead of generating file",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Output metrics as JSON",
    )

    args = parser.parse_args()

    root = find_project_root()

    try:
        print("📊 Collecting repository metrics...", file=sys.stderr)
        repo_metrics = collect_git_metrics(root)

        print("🧪 Collecting test metrics...", file=sys.stderr)
        test_metrics = collect_test_metrics(root)

        print("🔍 Collecting code quality metrics...", file=sys.stderr)
        quality_metrics = collect_code_quality_metrics(root)

        print("📈 Evaluating coverage policy...", file=sys.stderr)
        coverage_policy = collect_coverage_policy(root)

        health = RepositoryHealth(
            repository=repo_metrics,
            tests=test_metrics,
            code_quality=quality_metrics,
            coverage_policy=coverage_policy,
            overall_status="",
        )
        health.overall_status = assess_health(health)

    except Exception as e:
        print(f"❌ Error collecting metrics: {e}", file=sys.stderr)
        return 1

    if args.summary:
        print_summary(health)
        return 0

    try:
        if args.json:
            import json

            metrics_dict = {
                "repository": {
                    "total_commits": health.repository.total_commits,
                    "python_files": health.repository.python_files,
                    "lines_of_code": health.repository.lines_of_code,
                    "git_size_kb": health.repository.git_size_kb,
                    "project_size_mb": health.repository.project_size_mb,
                    "working_tree_clean": health.repository.working_tree_clean,
                    "branch_name": health.repository.branch_name,
                    "head_sha": health.repository.head_sha,
                    "collected_at_utc": health.repository.collected_at_utc,
                },
                "tests": {
                    "total_passed": health.tests.total_passed,
                    "total_failed": health.tests.total_failed,
                    "execution_time_sec": health.tests.execution_time_sec,
                    "coverage_percent": health.tests.coverage_percent,
                    "collection_error": health.tests.collection_error,
                },
                "code_quality": {
                    "mypy_issues": health.code_quality.mypy_issues,
                    "ruff_issues": health.code_quality.ruff_issues,
                    "formatting_compliant": health.code_quality.formatting_compliant,
                    "type_safe": health.code_quality.type_safe,
                    "collection_errors": health.code_quality.collection_errors,
                },
                "coverage_policy": {
                    "passed": health.coverage_policy.passed,
                    "rows": health.coverage_policy.rows,
                    "errors": health.coverage_policy.errors,
                },
                "overall_status": health.overall_status,
            }
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(metrics_dict, indent=2))
            print(f"✅ Metrics saved to {args.json}", file=sys.stderr)

        output_path = args.output or root / "runtime" / "health_check_report.md"
        report = generate_report(health, root)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        assert_registered_output(root, "health_check_report", output_path)
        atomic_write(output_path, report)

        print(f"✅ Report generated: {output_path.relative_to(root)}", file=sys.stderr)
        print_summary(health)

        return 0

    except Exception as e:
        print(f"❌ Error generating report: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
