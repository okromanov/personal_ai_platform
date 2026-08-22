from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from operations.scripts.quality.registry import (
    evidence_results,
    impacted_profiles,
    load_quality_registry,
    profiles_for_milestone,
    validate_evidence_record,
    validate_quality_registry,
    validate_server_source,
)
from operations.scripts.status.generate_project_status import collect_milestones


class QualityRegistryTests(unittest.TestCase):
    def test_server_evidence_schema_rejects_forgery_stale_sha_and_bad_artifacts(self) -> None:
        source = {
            "repository": "owner/repo",
            "workflow": "Project check",
            "run_id": "123",
            "run_url": "https://github.com/owner/repo/actions/runs/123",
            "event_sha": "a" * 40,
        }
        record = {
            "type": "test_evidence",
            "evidence_id": "contract",
            "result": "passed",
            "git_sha": "a" * 40,
            "checked_at": "2026-08-21T10:00:00Z",
            "environment": {"os": "linux"},
            "command": ["python3", "-m", "unittest"],
            "exit_code": 0,
            "artifacts": [{"path": "result.txt", "bytes": 10, "sha256": "b" * 64}],
            "server_source": source,
        }
        self.assertEqual(
            validate_evidence_record(
                record,
                evidence_id="contract",
                expected_type="test_evidence",
                expected_sha="a" * 40,
            ),
            [],
        )
        stale = {**record, "git_sha": "c" * 40}
        self.assertTrue(
            any(
                "текущим SHA" in error
                for error in validate_evidence_record(
                    stale,
                    evidence_id="contract",
                    expected_type="test_evidence",
                    expected_sha="a" * 40,
                )
            )
        )
        forged = {**record, "command": [], "exit_code": 9, "artifacts": []}
        forged_errors = validate_evidence_record(
            forged,
            evidence_id="contract",
            expected_type="test_evidence",
            expected_sha="a" * 40,
        )
        self.assertTrue(any("command" in error for error in forged_errors))
        self.assertTrue(any("exit_code" in error for error in forged_errors))
        self.assertTrue(any("artifacts" in error for error in forged_errors))
        self.assertTrue(validate_server_source({}, expected_sha="a" * 40))
        invalid_source = {
            "repository": "owner/repo",
            "workflow": "Project check",
            "run_id": "not-numeric",
            "run_url": "https://example.invalid/run",
            "event_sha": "short",
            "artifact_id": "not-numeric",
            "artifact_digest": "not-a-digest",
        }
        source_errors = validate_server_source(
            invalid_source, expected_sha="a" * 40, require_artifact=True
        )
        self.assertTrue(any("event_sha" in error for error in source_errors))
        self.assertTrue(any("run_id" in error for error in source_errors))
        self.assertTrue(any("run_url" in error for error in source_errors))
        self.assertTrue(any("artifact_id" in error for error in source_errors))
        self.assertTrue(any("artifact_digest" in error for error in source_errors))

    def test_invalid_registry_reports_every_schema_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "operations").mkdir()
            path = root / "operations/quality_registry.json"

            with self.assertRaisesRegex(ValueError, "Отсутствует"):
                load_quality_registry(Path(tmp) / "missing")
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                load_quality_registry(root)

            invalid = {
                "evidence_catalog": {
                    "scalar": "bad",
                    "bad_class": {"class": "mandatory", "source": ""},
                    "bad_record": {"class": "hard", "source": "record:../outside.json"},
                    "broken_json": {
                        "class": "hard",
                        "source": "record:runtime/broken.json",
                    },
                },
                "profiles": {
                    "scalar": "bad",
                    "invalid": {
                        "milestones": ["m99"],
                        "required_evidence": ["missing"],
                        "paths": [""],
                        "scope_coverage": "unknown",
                    },
                    "global": {
                        "milestones": [],
                        "required_evidence": [],
                        "paths": [],
                        "scope_coverage": "global_evidence",
                        "scope_evidence": [],
                    },
                },
            }
            (root / "runtime").mkdir()
            (root / "runtime/broken.json").write_text("{", encoding="utf-8")
            path.write_text(json.dumps(invalid), encoding="utf-8")
            errors = validate_quality_registry(root, {"m01"})

            joined = "\n".join(errors)
            for fragment in [
                "evidence scalar",
                "class должен",
                "отсутствует source",
                "некорректный путь record",
                "quality profile scalar",
                "неизвестный scope_coverage",
                "неизвестный milestone",
                "неизвестный evidence",
                "global_evidence требует scope_evidence",
            ]:
                self.assertIn(fragment, joined)

    def test_profile_selection_and_impact_ignore_malformed_rows(self) -> None:
        registry: dict[str, object] = {
            "profiles": {
                "bad": "scalar",
                "m02": {"milestones": ["M02"], "paths": ["src/**"]},
            }
        }
        self.assertEqual(profiles_for_milestone({"profiles": []}, "m02"), [])
        self.assertEqual([row[0] for row in profiles_for_milestone(registry, "m02")], ["m02"])
        self.assertEqual(impacted_profiles({"profiles": []}, ["src/a.py"]), [])
        self.assertEqual(impacted_profiles(registry, ["./src/a.py"]), ["m02"])

    def test_evidence_sources_cover_checker_named_checks_and_records(self) -> None:
        registry: dict[str, object] = {
            "evidence_catalog": {
                "project": {"class": "hard", "source": "checker"},
                "unit": {"class": "hard", "source": "unit_tests"},
                "named": {"class": "advisory", "source": "check:traceability"},
                "future": {"class": "hard", "source": "future"},
                "failed": {"class": "hard", "source": "record:failed.json"},
                "broken": {"class": "hard", "source": "record:broken.json"},
                "outside": {"class": "hard", "source": "record:../outside.json"},
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "failed.json").write_text(
                json.dumps(
                    {
                        "result": "failed",
                        "git_sha": "a" * 40,
                        "checked_at": "now",
                        "environment": {"os": "linux"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "broken.json").write_text("{", encoding="utf-8")
            result = evidence_results(
                registry,
                root=root,
                check_summary={"ok": True, "checks": [{"name": "traceability", "ok": False}]},
                unit_summary={"ok": False},
                context={"git_sha": "fallback", "timestamp": "later"},
            )

        self.assertEqual(result["project"]["result"], "passed")
        self.assertEqual(result["unit"]["result"], "failed")
        self.assertEqual(result["named"]["result"], "failed")
        self.assertEqual(result["failed"]["git_sha"], "a" * 40)
        self.assertEqual(result["future"]["result"], "missing")
        self.assertEqual(result["broken"]["result"], "missing")
        self.assertEqual(result["outside"]["result"], "missing")

    def test_repository_registry_defines_only_current_quality_horizon(self) -> None:
        root = Path(__file__).resolve().parents[3]
        registry = load_quality_registry(root)
        profiles = registry["profiles"]
        catalog = registry["evidence_catalog"]
        self.assertIsInstance(profiles, dict)
        self.assertIsInstance(catalog, dict)
        if not isinstance(profiles, dict) or not isinstance(catalog, dict):
            self.fail("registry profiles/catalog must be objects")
        self.assertIn("foundation", profiles)
        self.assertEqual(
            set(catalog),
            {
                "project_checks",
                "unit_tests",
                "quality_suite",
                "m02_contract_tests",
                "m02_security_tests",
                "m02_e2e_tests",
                "m02_infrastructure_tests",
            },
        )
        foundation = profiles["foundation"]
        self.assertIsInstance(foundation, dict)
        if isinstance(foundation, dict):
            self.assertEqual(
                foundation["required_evidence"],
                ["project_checks", "unit_tests", "quality_suite"],
            )
        raw_milestones = collect_milestones(root)["items"]
        self.assertIsInstance(raw_milestones, list)
        milestone_items = (
            [item for item in raw_milestones if isinstance(item, dict)]
            if isinstance(raw_milestones, list)
            else []
        )
        milestones = {str(item["id"]) for item in milestone_items}
        self.assertEqual(validate_quality_registry(root, milestones), [])

        covered = {
            str(milestone).lower()
            for profile in profiles.values()
            if isinstance(profile, dict)
            for milestone in profile.get("milestones", [])
        }
        milestone_state = collect_milestones(root)
        state_items = milestone_state["items"]
        self.assertIsInstance(state_items, list)
        required_profiles = {
            str(item["id"])
            for item in state_items
            if isinstance(item, dict)
            if str(item["work_state"]) in {"in-progress", "completed"}
        }
        self.assertTrue(required_profiles <= covered)
        current = milestone_state["current"]
        self.assertIsInstance(current, dict)
        if isinstance(current, dict) and str(current["work_state"]) == "planned":
            self.assertNotIn(str(current["id"]), covered)

    def test_manual_record_changes_missing_to_passed(self) -> None:
        registry = {
            "evidence_catalog": {
                "manual": {
                    "class": "hard",
                    "source": "record:work/evidence/manual.json",
                    "record_type": "test_evidence",
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = evidence_results(
                registry,
                root=root,
                check_summary={"ok": True, "checks": []},
                unit_summary={"ok": True},
            )
            self.assertEqual(missing["manual"]["result"], "missing")
            (root / "work/evidence").mkdir(parents=True)
            (root / "work/evidence/manual.json").write_text(
                json.dumps(
                    {
                        "type": "test_evidence",
                        "evidence_id": "manual",
                        "result": "passed",
                        "git_sha": "a" * 40,
                        "checked_at": "2026-08-21T10:00:00Z",
                        "environment": {"os": "linux"},
                        "command": ["python3", "test.py"],
                        "exit_code": 0,
                        "artifacts": [{"path": "result.txt", "bytes": 1, "sha256": "b" * 64}],
                        "server_source": {
                            "repository": "owner/repo",
                            "workflow": "Project check",
                            "run_id": "1",
                            "run_url": "https://github.com/owner/repo/actions/runs/1",
                            "event_sha": "a" * 40,
                        },
                    }
                ),
                encoding="utf-8",
            )
            passed = evidence_results(
                registry,
                root=root,
                check_summary={"ok": True, "checks": []},
                unit_summary={"ok": True},
                context={"git_sha": "a" * 40},
            )
            self.assertEqual(passed["manual"]["result"], "passed")


if __name__ == "__main__":
    unittest.main()
