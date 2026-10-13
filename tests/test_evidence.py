"""Exercise real processes, stale XML, failures, timeouts and report/evidence bindings."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import test_report as fixtures

MODULE = fixtures.MODULE


class EvidenceTests(unittest.TestCase):
    setUp = fixtures.ReportTests.setUp
    completed = fixtures.ReportTests.completed
    with_collected_evidence = fixtures.ReportTests.with_collected_evidence
    policy_gate = fixtures.ReportTests.policy_gate

    def collect(self, check_id, kind, code, **options):
        from collect_evidence import collect
        directory = self.root / ".java-modernize"
        directory.mkdir(exist_ok=True)
        path = directory / "policy.json"
        path.write_text(json.dumps(self.policy))
        return collect(self.root, path, check_id, kind, [sys.executable, "-c", code], **options)

    def test_process_failures_timeouts_and_changed_inputs_are_not_passing(self):
        self.completed()
        failed = self.collect("fails", "build", "raise SystemExit(7)")
        self.assertEqual(failed["record"]["exit_code"], 7)
        self.assertEqual(failed["check"]["status"], "failed")
        timeout = self.collect("timeout", "build", "import time; time.sleep(10)", timeout=1)
        self.assertTrue(timeout["record"]["timed_out"])
        changed = self.collect("changes", "build", "from pathlib import Path; Path('pom.xml').write_text('changed')")
        self.assertIn("Validation command changed project inputs", changed["record"]["problems"])
        self.assertTrue(failed["record"]["tool_versions"])

    def test_stale_zero_and_failed_test_xml_reject_even_successful_process(self):
        self.completed()
        directory = self.root / "target"
        directory.mkdir()
        xml = directory / "TEST-suite.xml"
        xml.write_text('<testsuite tests="1" skipped="0" failures="0" errors="0"/>')
        stale = self.collect("stale", "unit-tests", "print('not running tests')", test_globs=["target/TEST-*.xml"])
        self.assertEqual(stale["check"]["status"], "failed")
        for label, attrs in [("zero", 'tests="0" skipped="0" failures="0" errors="0"'), ("failure", 'tests="1" skipped="0" failures="1" errors="0"')]:
            code = "from pathlib import Path; Path('target/TEST-suite.xml').write_text(" + repr("<testsuite " + attrs + "/>") + ")"
            result = self.collect(label, "unit-tests", code, test_globs=["target/TEST-*.xml"])
            self.assertEqual(result["check"]["status"], "failed")

    def test_gate_rejects_changed_process_status_command_counts_and_graph(self):
        report = self.with_collected_evidence(self.completed())
        self.assertEqual(self.policy_gate(report), [])
        for mutation in ("command", "count", "graph-kind", "failed-record", "missing-record"):
            changed = copy.deepcopy(report)
            if mutation == "command":
                changed["checks"][0]["command"] = "another command"
            elif mutation == "count":
                changed["checks"][1]["tests_after"] = 6
            elif mutation == "graph-kind":
                graph_id = changed["inputs_snapshot"]["graphs"][0]["artifact_ids"][0]
                next(a for a in changed["artifacts"] if a["id"] == graph_id)["kind"] = "log"
            elif mutation == "missing-record":
                changed["checks"][0].pop("execution_artifact_id")
            else:
                item = next(a for a in changed["artifacts"] if a["id"] == changed["checks"][0]["execution_artifact_id"])
                path = self.root / item["path"]
                original = path.read_bytes()
                record = json.loads(original)
                record["exit_code"] = 1
                path.write_text(json.dumps(record))
                item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertTrue(self.policy_gate(changed), mutation)
            if mutation == "failed-record":
                path.write_bytes(original)

    def test_collection_does_not_overwrite_and_redacts_argument_secrets(self):
        self.completed()
        self.collect("once", "build", "print('ok')")
        with self.assertRaises(FileExistsError):
            self.collect("once", "build", "print('ok')")
        from collect_evidence import display_argv
        command = display_argv(["tool", "--password=private", "--token", "private2", "https://user:private3@example.com"])
        self.assertNotIn("private", command)

    def test_run_evidence_is_isolated_and_unsafe_run_paths_reject(self):
        self.completed()
        first = "20261013T120000123456Z-first"
        second = "20261013T120000123457Z-second"
        a = self.collect("build", "build", "print('first')", run_id=first)
        b = self.collect("build", "build", "print('second')", run_id=second)
        self.assertNotEqual(a["artifacts"][0]["path"], b["artifacts"][0]["path"])
        self.assertIn("/runs/" + first + "/evidence/", a["artifacts"][0]["path"])
        with self.assertRaises(FileExistsError):
            self.collect("build", "build", "print('no overwrite')", run_id=first)
        for value in ("../escape", first + "/nested", first + "\\nested"):
            with self.assertRaises(ValueError):
                self.collect("unsafe", "build", "raise SystemExit(99)", run_id=value)

    def test_baseline_xml_is_retained_and_counts_cannot_be_invented(self):
        report = self.completed()
        baseline = self.collect("baseline", "baseline", "from pathlib import Path; p=Path('target/TEST-fixture.xml'); p.parent.mkdir(exist_ok=True); p.write_text('<testsuite tests=\"3\" skipped=\"0\" failures=\"0\" errors=\"0\"/>')", test_globs=["target/TEST-*.xml"])
        report["artifacts"] += baseline["artifacts"]
        report = self.with_collected_evidence(report)
        report["checks"][1].update(tests_before=3, baseline_execution_artifact_id=baseline["check"]["execution_artifact_id"])
        self.assertEqual(self.policy_gate(report), [])
        report["checks"][1]["tests_before"] = 4
        self.assertTrue(self.policy_gate(report))


if __name__ == "__main__":
    unittest.main()
