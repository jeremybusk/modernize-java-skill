"""Exercise portable run output, canonical rendering, and repository coordination."""

import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote
import re

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "java-modernize/scripts"))
import run_documents as runs


class RunDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace with spaces"
        self.root.mkdir()
        (self.root / "pom.xml").write_text("synthetic project input", encoding="utf-8")

    def initialize(self, **options):
        return runs.initialize(self.root, "java-maintenance", {"app": "."}, **options)

    def test_timestamped_files_do_not_collide_and_pointer_is_portable(self):
        first = self.initialize()
        original = {p.name: p.read_bytes() for p in first.parent.iterdir()}
        second = self.initialize()
        self.assertNotEqual(first, second)
        data = runs.render(first, check=True)
        self.assertEqual(len(list(first.parent.glob("*.md"))), 6)
        self.assertTrue(all(p.name.startswith(data["run_id"]) for p in first.parent.iterdir()))
        self.assertEqual(original, {p.name: p.read_bytes() for p in first.parent.iterdir()})
        pointer = runs.read_json(self.root / ".java-modernize/latest.json")
        self.assertEqual((self.root / ".java-modernize" / pointer["manifest"]), second)
        moved = self.root.parent / "moved"
        shutil.copytree(self.root, moved)
        runs.render(moved / first.relative_to(self.root), check=True)

    def test_compact_layout_and_cli_root_are_independent_of_cwd(self):
        call = subprocess.run([sys.executable, str(ROOT / "java-modernize/scripts/run_documents.py"), "init", "--scope-root", str(self.root), "--slug", "audit", "--repo", "app=.", "--layout", "compact", "--mode", "audit"], cwd=self.root.parent, capture_output=True, text=True)
        self.assertEqual(call.returncode, 0, call.stderr)
        manifest = Path(json.loads(call.stdout)["manifest"])
        self.assertEqual(len(list(manifest.parent.glob("*.md"))), 2)
        runs.render(manifest, check=True)
        data = runs.read_json(manifest)
        data["layout"] = "expanded"
        runs.write_json(manifest, data)
        with self.assertRaises(ValueError):
            runs.render(manifest)

    def test_same_timestamp_refuses_to_overwrite(self):
        with patch.object(runs, "utc_now", return_value="2026-10-13T12:00:00.123456Z"):
            manifest = self.initialize()
            before = manifest.read_bytes()
            with self.assertRaises(FileExistsError):
                self.initialize()
            self.assertEqual(before, manifest.read_bytes())

    def test_manifest_scope_and_dependency_errors_reject(self):
        manifest = self.initialize()
        data = runs.read_json(manifest)
        for mutation in ("duplicate", "cycle", "escape", "overlap", "future-created"):
            changed = copy.deepcopy(data)
            if mutation == "duplicate":
                changed["repositories"].append(copy.deepcopy(changed["repositories"][0]))
            elif mutation == "cycle":
                changed["repositories"][0]["depends_on"] = ["app"]
            elif mutation == "escape":
                changed["repositories"][0]["path"] = "../outside"
            elif mutation == "overlap":
                other = copy.deepcopy(changed["repositories"][0])
                other.update(id="other", path="submodule")
                changed["repositories"].append(other)
                changed["scope_kind"] = "workspace"
            else:
                changed["created_at"] = "2099-01-01T00:00:00Z"
            with self.assertRaises(ValueError, msg=mutation):
                runs.validate_manifest(changed)

    def test_render_escapes_authored_content_and_rejects_markdown_drift(self):
        manifest = self.initialize()
        data = runs.read_json(manifest)
        data["title"] = "A | B\n<script>bad</script> [click](https://example.com)"
        runs.write_json(manifest, data)
        runs.render(manifest)
        index = manifest.parent / (data["run_id"] + "-index.md")
        content = index.read_text(encoding="utf-8")
        self.assertNotIn("<script>", content)
        self.assertNotIn("[click](https://example.com)", content)
        index.write_text(content + "\nImplementation complete!", encoding="utf-8")
        with self.assertRaises(ValueError):
            runs.render(manifest, check=True)
        runs.render(manifest)
        runs.render(manifest, check=True)

    def test_review_links_and_generated_relative_links_survive_space_paths(self):
        manifest = self.initialize(mode="audit")
        data = runs.read_json(manifest)
        data["links"] = [{"label": "CI result", "url": "https://example.com/runs/42"}]
        report = runs.read_json(ROOT / "java-modernize/assets/enterprise-report.example.json")
        artifact = self.root / ".java-modernize/evidence with spaces.log"
        artifact.write_text("Synthetic log", encoding="utf-8")
        report["artifacts"] = [{"id": "log", "path": artifact.relative_to(self.root).as_posix(), "sha256": runs.digest_file(artifact)}]
        path = manifest.parent / (data["run_id"] + "-evidence-report.json")
        runs.write_json(path, report)
        runs.write_json(manifest, data)
        runs.bind_report(manifest, "app", path.relative_to(self.root).as_posix())
        for document in manifest.parent.glob("*.md"):
            content = document.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)", content):
                if not target.startswith("https://"):
                    self.assertTrue((document.parent / unquote(target)).is_file(), target)
        summary = manifest.parent / (data["run_id"] + "-completion-summary.md")
        self.assertIn("[CI result](https://example.com/runs/42)", summary.read_text())
        data = runs.read_json(manifest)
        data["links"][0]["url"] = "https://user:secret@example.com/run"
        with self.assertRaises(ValueError):
            runs.validate_manifest(data)

    def test_bound_report_drift_and_missing_evidence_link_reject(self):
        manifest = self.initialize(mode="audit")
        data = runs.read_json(manifest)
        report = runs.read_json(ROOT / "java-modernize/assets/enterprise-report.example.json")
        path = manifest.parent / (data["run_id"] + "-evidence-report.json")
        runs.write_json(path, report)
        data["repositories"][0]["report"] = {"path": path.relative_to(self.root).as_posix(), "sha256": runs.digest_file(path)}
        runs.write_json(manifest, data)
        runs.render(manifest)
        runs.render(manifest, check=True)
        report["next_actions"] = ["Recheck unavailable mirror"]
        runs.write_json(path, report)
        with self.assertRaises(ValueError):
            runs.render(manifest)
        data["repositories"][0]["report"]["sha256"] = runs.digest_file(path)
        runs.write_json(manifest, data)
        runs.render(manifest)
        report["artifacts"] = [{"id": "missing", "path": "missing.log", "sha256": "0" * 64}]
        runs.write_json(path, report)
        data["repositories"][0]["report"]["sha256"] = runs.digest_file(path)
        runs.write_json(manifest, data)
        with self.assertRaises(ValueError):
            runs.render(manifest)

    def test_symlink_output_cannot_redirect_writes(self):
        elsewhere = self.root.parent / "elsewhere"
        elsewhere.mkdir()
        try:
            (self.root / ".java-modernize").symlink_to(elsewhere, target_is_directory=True)
        except OSError:
            self.skipTest("Directory symlinks unavailable")
        with self.assertRaises(ValueError):
            self.initialize()
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_phase_completion_and_dependency_order_cannot_be_invented(self):
        manifest = self.initialize()
        data = runs.read_json(manifest)
        data["phases"]["completion"].update(status="complete", summary="Done")
        with self.assertRaises(ValueError):
            runs.validate_manifest(data)
        for phase in data["phases"].values():
            phase.update(status="complete", summary="Claimed complete")
        with self.assertRaises(ValueError):
            runs.validate_manifest(data)
        data["mode"] = "audit"
        runs.write_json(manifest, data)
        with self.assertRaises(ValueError):
            runs.render(manifest)

    def test_checkpoint_detects_input_change_and_invalidates_dependents(self):
        for name in ("platform", "service"):
            (self.root / name).mkdir()
            (self.root / name / "pom.xml").write_text("input", encoding="utf-8")
        manifest = runs.initialize(self.root, "workspace", {"platform": "platform", "service": "service"}, scope_kind="workspace")
        data = runs.read_json(manifest)
        data["repositories"][1]["depends_on"] = ["platform"]
        data["phases"]["assessment"].update(status="complete", summary="Observed baseline")
        runs.write_json(manifest, data)
        runs.render(manifest)
        runs.checkpoint(manifest, {})
        self.assertEqual(runs.resume(manifest, {}), [])
        (self.root / "platform/pom.xml").write_text("changed", encoding="utf-8")
        self.assertEqual(runs.resume(manifest, {}), ["platform", "service"])
        changed = runs.read_json(manifest)
        self.assertEqual(changed["phases"]["assessment"]["status"], "stale")
        self.assertEqual((self.root / "platform/pom.xml").read_text(), "changed")
        runs.render(manifest, check=True)

    def test_missing_checkpoint_is_unknown_and_changed_checkpoint_cannot_refresh_itself(self):
        manifest = self.initialize()
        self.assertEqual(runs.resume(manifest, {}), ["app"])
        runs.checkpoint(manifest, {})
        self.assertEqual(runs.resume(manifest, {}), [])
        data = runs.read_json(manifest)
        saved = self.root / data["repositories"][0]["checkpoint"]["path"]
        saved.write_text("{}", encoding="utf-8")
        self.assertEqual(runs.resume(manifest, {}), ["app"])
        self.assertEqual(saved.read_text(), "{}")

    def test_audit_completion_is_distinct_from_implementation_gate(self):
        manifest = self.initialize(mode="audit", layout="compact")
        data = runs.read_json(manifest)
        report = runs.read_json(ROOT / "java-modernize/assets/enterprise-report.example.json")
        report["status"] = "complete"
        report_path = manifest.parent / (data["run_id"] + "-evidence-report.json")
        runs.write_json(report_path, report)
        runs.bind_report(manifest, "app", report_path.relative_to(self.root).as_posix())
        data = runs.read_json(manifest)
        for phase in data["phases"].values():
            phase.update(status="complete", summary="Audit observations and proposals recorded")
        for phase in ("execution", "validation"):
            data["phases"][phase].update(status="not_applicable", summary="Audit only; no implementation or application validation requested")
        runs.write_json(manifest, data)
        runs.render(manifest)
        runs.render(manifest, check=True)
        with self.assertRaises(ValueError):
            runs.check_completion(manifest, {})


class RunCompletionTests(unittest.TestCase):
    def setUp(self):
        import test_report as fixtures
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixtures = {}
        for name in ("platform", "service"):
            case = fixtures.ReportTests()
            case.setUp()
            self.addCleanup(case.doCleanups)
            case.root = self.root / name
            case.root.mkdir()
            self.fixtures[name] = case
        self.manifest = runs.initialize(self.root, "coordinated", {name: name for name in self.fixtures}, scope_kind="workspace")

    def prepare_complete(self):
        from collect_evidence import collect
        data = runs.read_json(self.manifest)
        run_id = data["run_id"]
        policies = {}
        for name, case in self.fixtures.items():
            # Exercise the actual collector's new run location through the existing gate.
            with patch("collect_evidence.collect", side_effect=lambda *args, **kwargs: collect(*args, **kwargs, run_id=run_id)):
                report = case.with_collected_evidence(case.completed())
            self.assertEqual(case.policy_gate(report), [])
            path = case.root / ".java-modernize/runs" / run_id / (run_id + "-evidence-report.json")
            runs.write_json(path, report)
            runs.bind_report(self.manifest, name, path.relative_to(case.root).as_posix())
            policies[name] = str(case.root / ".java-modernize/policy.json")
        data = runs.read_json(self.manifest)
        data["repositories"][1]["depends_on"] = ["platform"]
        data["batches"] = [{"id": name, "repositories": [name], "depends_on": ["platform"] if name == "service" else [], "status": "complete", "goal": "Synthetic process validation", "files": [name + ":pom.xml"], "validation": "Recorded build, tests, graph", "recovery": "Restore only agent-owned changes", "result": "Synthetic checks passed"} for name in self.fixtures]
        for phase in data["phases"].values():
            phase.update(status="complete", summary="Completed synthetic fixture checks")
        data["updated_at"] = runs.utc_now()
        runs.write_json(self.manifest, data)
        runs.render(self.manifest)
        return policies

    def test_all_repository_gates_use_collected_evidence_and_independent_policy(self):
        policies = self.prepare_complete()
        runs.check_completion(self.manifest, policies)
        call = subprocess.run([sys.executable, str(ROOT / "java-modernize/scripts/run_documents.py"), "check", str(self.manifest), "--require-complete", "--policy", "platform=" + policies["platform"], "--policy", "service=" + policies["service"]], capture_output=True, text=True)
        self.assertEqual(call.returncode, 0, call.stderr + call.stdout)
        self.assertTrue(json.loads(call.stdout)["live_completion_checked"])
        with self.assertRaises(ValueError):
            runs.check_completion(self.manifest, {"platform": policies["platform"]})
        (self.root / "service/pom.xml").write_text("changed after validation", encoding="utf-8")
        # Historical documents remain inspectable, but current completion cannot pass.
        runs.render(self.manifest, check=True)
        with self.assertRaises(ValueError):
            runs.check_completion(self.manifest, policies)

    def test_one_partial_repository_prevents_overall_completion(self):
        self.prepare_complete()
        data = runs.read_json(self.manifest)
        repo = data["repositories"][1]
        path = self.root / repo["path"] / repo["report"]["path"]
        report = runs.read_json(path)
        report["status"] = "partial"
        runs.write_json(path, report)
        repo["report"]["sha256"] = runs.digest_file(path)
        runs.write_json(self.manifest, data)
        with self.assertRaises(ValueError):
            runs.render(self.manifest)

    def test_changed_policy_invalidates_checkpoint_without_rebinding_reports(self):
        policies = self.prepare_complete()
        runs.checkpoint(self.manifest, policies)
        self.assertEqual(runs.resume(self.manifest, policies), [])
        path = Path(policies["platform"])
        path.write_text(path.read_text() + "\n", encoding="utf-8")
        self.assertEqual(runs.resume(self.manifest, policies), ["platform", "service"])
        self.assertEqual(runs.read_json(self.manifest)["phases"]["completion"]["status"], "stale")
        with self.assertRaises(ValueError):
            runs.check_completion(self.manifest, policies)


if __name__ == "__main__":
    unittest.main()
