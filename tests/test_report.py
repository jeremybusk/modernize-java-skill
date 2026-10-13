"""Report gates prevent incomplete/contradictory evidence from being accepted as complete."""

import copy
from datetime import datetime, timedelta, timezone
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
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("validate_report", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.report = json.loads((ROOT / "java-modernize/assets/enterprise-report.example.json").read_text())
        self.policy = json.loads((ROOT / "java-modernize/assets/project-policy.example.json").read_text())
        self.policy["source"] = self.report["policy"]["source"]
        self.policy["components"][0]["id"] = "platform"

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
        report["inputs_snapshot"] = {"captured_at": report["generated_at"], "files": MODULE.capture(self.root), "graphs": [{"module": report["modules"][0]["path"], "artifact_ids": ["build-log"]}]}
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
        report = self.with_collected_evidence(self.completed())
        marker = self.root / "command-was-executed"
        path = self.root / ".java-modernize/report.json"
        policy_path = path.parent / "policy.json"
        policy_bytes = json.dumps(self.policy).encode()
        policy_path.write_bytes(policy_bytes)
        report["policy_binding"] = {"sha256": hashlib.sha256(policy_bytes).hexdigest()}
        path.write_text(json.dumps(report))
        call = subprocess.run([sys.executable, str(SCRIPT), str(path), "--project-root", str(self.root), "--require-complete", "--policy", str(policy_path)], capture_output=True, text=True)
        self.assertEqual(call.returncode, 0, call.stderr + call.stdout)
        self.assertTrue(json.loads(call.stdout)["artifact_hashes_checked"])
        self.assertFalse(marker.exists())

    def test_live_gate_rejects_historical_evidence_without_breaking_archive_validation(self):
        report = self.completed()
        self.assertEqual(MODULE.validate(report, self.root), [])
        now = MODULE.timestamp(report["generated_at"]) + timedelta(days=30)
        self.assertTrue(any("age" in e for e in MODULE.validate(report, self.root, require_complete=True, now=now)))
        self.assertTrue(any("later than validation" in e for e in MODULE.validate(report, self.root, require_complete=True, now=MODULE.timestamp(report["generated_at"]) - timedelta(days=1))))

    def test_input_snapshot_catches_changed_added_and_deleted_sources(self):
        for mutation in ("add", "change", "delete"):
            report = self.completed()
            if mutation == "add":
                (self.root / "New.java").write_text("class New {}")
            elif mutation == "change":
                (self.root / "test.log").write_text("different input")
            else:
                (self.root / "test.log").unlink()
            errors = MODULE.validate(report, self.root, require_complete=True, now=MODULE.timestamp(report["generated_at"]))
            self.assertTrue(any("input set" in e for e in errors), mutation)
            (self.root / "New.java").unlink(missing_ok=True)

    def test_live_gate_requires_snapshot_and_every_module_graph(self):
        report = self.completed()
        report.pop("inputs_snapshot")
        self.assertTrue(any("snapshot" in e for e in MODULE.validate(report, self.root, require_complete=True)))
        report = self.completed()
        report["inputs_snapshot"]["graphs"][0]["module"] = "missing-module"
        self.assertTrue(any("every module" in e for e in MODULE.validate(report, self.root, require_complete=True)))

    def test_snapshot_rejects_symlink_input_and_preserves_wrapper_jar(self):
        report = self.completed()
        (self.root / "gradle/wrapper").mkdir(parents=True)
        (self.root / "gradle/wrapper/gradle-wrapper.jar").write_bytes(b"wrapper")
        self.assertIn("gradle/wrapper/gradle-wrapper.jar", MODULE.capture(self.root))
        try:
            (self.root / "source-link").symlink_to(self.root / "gradle", target_is_directory=True)
        except OSError:
            self.skipTest("Directory symlinks are unavailable")
        self.assertTrue(any("coverage" in e for e in MODULE.validate(report, self.root, require_complete=True)))

    def policy_gate(self, report, policy=None):
        policy = policy or self.policy
        digest = hashlib.sha256(json.dumps(policy).encode()).hexdigest()
        report["policy_binding"] = {"sha256": digest}
        return MODULE.validate(report, self.root, require_complete=True, now=MODULE.timestamp(report["generated_at"]), project_policy=policy, policy_sha256=digest)

    def test_policy_gate_accepts_matching_reviewed_scope(self):
        self.assertEqual(self.policy_gate(self.with_collected_evidence(self.completed())), [])

    def with_collected_evidence(self, report):
        # Synthetic process/XML fixtures test evidence plumbing, not Java semantics.
        from collect_evidence import collect
        directory = self.root / ".java-modernize"
        directory.mkdir(exist_ok=True)
        policy_path = directory / "policy.json"
        policy_path.write_text(json.dumps(self.policy))
        build = collect(self.root, policy_path, "build", "build", [sys.executable, "-c", "print('touch command-was-executed')"])
        tests = collect(self.root, policy_path, "tests", "unit-tests", [sys.executable, "-c", "from pathlib import Path; p=Path('target/TEST-fixture.xml'); p.parent.mkdir(exist_ok=True); p.write_text('<testsuite tests=\"5\" skipped=\"0\" failures=\"0\" errors=\"0\"/>')"], test_globs=["target/TEST-*.xml"])
        graph = collect(self.root, policy_path, "graph", "resolved-graph", [sys.executable, "-c", "from pathlib import Path; Path('target/graph.json').write_text('{\"fixture\":\"synthetic\"}')"], graph="target/graph.json")
        report["checks"] = [build["check"], tests["check"]]
        report["artifacts"] += build["artifacts"] + tests["artifacts"] + graph["artifacts"]
        report["inputs_snapshot"] = graph["inputs_snapshot"]
        report["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        for evidence in report["components"][0]["evidence"]:
            evidence["checked_at"] = report["generated_at"]
        return report

    def test_policy_prevents_report_weakening_checks_support_and_age(self):
        for mutation in ("missing-check", "support", "age", "scope", "owner", "version", "target", "exclusion"):
            report = self.completed()
            if mutation == "missing-check":
                policy = copy.deepcopy(self.policy)
                policy["checks"].append({"id": "consumer-contract", "kind": "contract", "allowed_statuses": ["passed"]})
                errors = self.policy_gate(report, policy)
            else:
                if mutation == "support":
                    report["policy"]["require_supported_updates"] = False
                elif mutation == "age":
                    report["policy"]["evidence_max_age_days"] = 999
                elif mutation == "scope":
                    report["components"] = []
                elif mutation == "owner":
                    report["components"][0]["owner"] = "test.log"
                elif mutation == "version":
                    report["components"][0]["selected"] = "2.0.0"
                elif mutation == "target":
                    report["modules"][0]["before"]["compilation_target"] = 21
                    report["modules"][0]["after"]["compilation_target"] = 21
                else:
                    (self.root / "src").mkdir(exist_ok=True)
                    (self.root / "src/Main.java").write_text("class Main {}")
                    # A report cannot shrink exclusions independently of policy.
                errors = self.policy_gate(report)
            self.assertTrue(errors, mutation)

    def test_policy_binding_rejects_changed_bytes_and_missing_policy(self):
        report = self.completed()
        self.assertTrue(any("independent" in e for e in MODULE.validate(report, self.root, require_complete=True)))
        self.assertTrue(any("binding" in e for e in MODULE.validate(report, self.root, require_complete=True, project_policy=self.policy, policy_sha256="f" * 64)))

    def test_policy_schema_rejects_unsafe_scope_duplicate_checks_and_missing_build(self):
        from policy import validate_policy
        self.assertEqual(validate_policy(self.policy), [])
        for mutation in ("unsafe", "duplicate", "no-build", "unknown-field", "unbounded-age"):
            policy = copy.deepcopy(self.policy)
            if mutation == "unsafe":
                policy["modules"][0]["path"] = "../outside"
            elif mutation == "duplicate":
                policy["checks"].append(copy.deepcopy(policy["checks"][0]))
            elif mutation == "no-build":
                policy["checks"] = policy["checks"][1:]
            elif mutation == "unknown-field":
                policy["unexpected"] = True
            else:
                policy["evidence_max_age_days"] = None
            self.assertTrue(validate_policy(policy), mutation)

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
