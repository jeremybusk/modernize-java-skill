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


if __name__ == "__main__":
    unittest.main()
