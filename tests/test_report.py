"""Report gates prevent incomplete/contradictory evidence from being accepted as complete."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "java-modernize/scripts/validate_report.py"
SPEC = importlib.util.spec_from_file_location("validate_report", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.report = json.loads((ROOT / "java-modernize/assets/enterprise-report.example.json").read_text())

    def completed(self):
        report = copy.deepcopy(self.report)
        report.update(mode="maintain-java", status="complete", freshness="verified")
        report["modules"][0]["before"].update(build_jvm=21, compiler_jdk=21, test_jvm=17)
        report["modules"][0]["after"] = copy.deepcopy(report["modules"][0]["before"])
        component = report["components"][0]
        component.update(current="1.0.0", selected="1.0.1", action="update", compatibility="verified", availability="available", support="supported")
        component["evidence"] = [
            {"kind": kind, "source": "Internal captured source for synthetic test fixture", "checked_at": "2026-10-12T17:00:00Z"}
            for kind in ("publication", "compatibility", "availability", "support")
        ]
        artifacts = []
        for artifact_id, name, content in [("owner", "pom.xml", b"synthetic version owner"), ("build-log", "build.log", b"build passed"), ("test-log", "test.log", b"executed 5 tests")]:
            (self.root / name).write_bytes(content)
            artifacts.append({"id": artifact_id, "path": name, "sha256": hashlib.sha256(content).hexdigest()})
        report["artifacts"] = artifacts
        report["checks"] = [
            {"id": "build", "kind": "build", "required": True, "status": "passed", "command": "fixture build", "environment": "synthetic", "reason": None, "artifact_ids": ["build-log"]},
            {"id": "tests", "kind": "unit-tests", "required": True, "status": "passed", "command": "fixture tests", "environment": "synthetic", "reason": None, "artifact_ids": ["test-log"], "tests_before": 5, "tests_after": 5},
        ]
        report["limitations"] = ["Synthetic fixture checks validate the reporting contract, not a real migration."]
        return report

    def test_partial_example_valid_but_complete_gate_rejects(self):
        self.assertIsNone(self.report["baseline"]["dirty"])
        self.assertEqual(MODULE.validate(self.report), [])
        path = self.root / "report.json"
        path.write_text(json.dumps(self.report))
        call = subprocess.run([sys.executable, str(SCRIPT), str(path), "--project-root", str(self.root), "--require-complete"], capture_output=True, text=True)
        self.assertEqual(call.returncode, 1)
        self.assertFalse(json.loads(call.stdout)["implementation_complete"])

    def test_completed_report_and_hash_gate(self):
        report = self.completed()
        self.assertEqual(MODULE.validate(report, self.root), [])
        (self.root / "pom.xml").write_bytes(b"changed after validation")
        self.assertTrue(any("hash" in error for error in MODULE.validate(report, self.root)))

    def test_preserved_test_runtime_is_independent_of_build_jvm(self):
        report = self.completed()
        report["modules"][0]["preserve"].append("test_jvm")
        report["modules"][0]["after"]["test_jvm"] = 21
        self.assertTrue(any("test_jvm" in error for error in MODULE.validate(report)))

    def test_complete_cli_verifies_hashes_without_executing_report_commands(self):
        report = self.completed()
        marker = self.root / "command-was-executed"
        report["checks"][0]["command"] = "touch command-was-executed"
        path = self.root / "report.json"
        path.write_text(json.dumps(report))
        call = subprocess.run([sys.executable, str(SCRIPT), str(path), "--project-root", str(self.root), "--require-complete"], capture_output=True, text=True)
        self.assertEqual(call.returncode, 0, call.stderr + call.stdout)
        self.assertTrue(json.loads(call.stdout)["artifact_hashes_checked"])
        self.assertFalse(marker.exists())

    def test_complete_cli_cannot_omit_hash_check_root(self):
        path = self.root / "report.json"
        path.write_text(json.dumps(self.completed()))
        call = subprocess.run([sys.executable, str(SCRIPT), str(path), "--require-complete"], capture_output=True, text=True)
        self.assertEqual(call.returncode, 2)

    def test_fixed_java_mode_rejects_higher_api_or_runtime(self):
        for role in ("compilation_target", "deployment_runtime"):
            report = self.completed()
            report["modules"][0]["preserve"] = []
            report["modules"][0]["after"][role] = 21
            self.assertTrue(any(role in error for error in MODULE.validate(report)))

    def test_complete_java_upgrade_must_meet_requested_target(self):
        report = self.completed()
        report["mode"] = "upgrade-java"
        report["modules"][0]["preserve"] = []
        report["modules"][0]["targets"] = {"deployment_runtime": 25}
        self.assertTrue(any("requested target" in error for error in MODULE.validate(report)))
        report["modules"][0]["targets"] = {}
        self.assertTrue(any("explicit requested" in error for error in MODULE.validate(report)))

    def test_missing_or_failed_required_checks_cannot_complete(self):
        for status in ("not_run", "failed", "not_applicable"):
            report = self.completed()
            report["checks"][1].update(status=status, reason="Environment unavailable")
            self.assertTrue(any("unmet required" in error for error in MODULE.validate(report)))
        report = self.completed()
        report["checks"] = report["checks"][1:]
        self.assertTrue(any("passing build" in error for error in MODULE.validate(report)))

    def test_zero_or_reduced_test_counts_require_attention(self):
        report = self.completed()
        report["checks"][1]["tests_after"] = 0
        self.assertTrue(any("nonzero" in error for error in MODULE.validate(report)))
        report["checks"][1]["tests_after"] = 3
        self.assertTrue(any("reduced" in error for error in MODULE.validate(report)))
        report["checks"][1]["tests_change_reason"] = "Two cases merged; migration evidence needs reviewer validation."
        self.assertEqual(MODULE.validate(report), [])

    def test_stale_or_future_evidence_and_invalid_dates_fail(self):
        for value in ("2026-09-01T00:00:00Z", "2026-10-13T00:00:00Z", "not-a-date", "2026-02-30T00:00:00Z", "2026-10-12T18:00:00"):
            report = self.completed()
            report["components"][0]["evidence"][0]["checked_at"] = value
            self.assertTrue(MODULE.validate(report), value)

    def test_publication_alone_cannot_prove_approved_availability(self):
        report = self.completed()
        report["components"][0]["evidence"] = report["components"][0]["evidence"][:1]
        self.assertTrue(any("source evidence" in error for error in MODULE.validate(report)))

    def test_missing_support_or_unknown_current_version_fail_completion(self):
        report = self.completed()
        report["components"][0]["support"] = "unverified"
        self.assertTrue(any("support" in error for error in MODULE.validate(report)))
        report = self.completed()
        report["components"][0]["current"] = None
        self.assertTrue(any("current" in error for error in MODULE.validate(report)))

    def test_duplicate_ids_or_unknown_references_fail(self):
        report = self.completed()
        report["checks"].append(copy.deepcopy(report["checks"][0]))
        self.assertTrue(any("duplicate" in error for error in MODULE.validate(report)))
        report = self.completed()
        report["checks"][0]["artifact_ids"] = ["missing"]
        self.assertTrue(any("unknown artifact" in error for error in MODULE.validate(report)))

    def test_unsafe_paths_and_symlink_artifacts_fail(self):
        for path in ("../outside.log", "/outside.log", "C:/outside.log", "dir\\outside.log"):
            report = self.completed()
            report["artifacts"][0]["path"] = path
            self.assertTrue(any("unsafe" in error for error in MODULE.validate(report, self.root)))
        report = self.completed()
        (self.root / "pom.xml").unlink()
        try:
            (self.root / "pom.xml").symlink_to(self.root / "build.log")
        except OSError:
            self.skipTest("Symlink creation is unavailable on this platform")
        self.assertTrue(any("unsafe" in error for error in MODULE.validate(report, self.root)))

    def test_invalid_values_are_not_echoed_in_errors(self):
        report = self.completed()
        report["status"] = "private-secret-value"
        errors = MODULE.validate(report)
        self.assertTrue(errors)
        self.assertNotIn("private-secret-value", " ".join(errors))

    def test_duplicate_json_keys_rejected_by_cli(self):
        path = self.root / "report.json"
        path.write_text('{"schema_version": 1, "schema_version": 1}')
        call = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
        self.assertEqual(call.returncode, 2)


if __name__ == "__main__":
    unittest.main()
