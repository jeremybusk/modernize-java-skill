"""Verify exported resource/notice integrity and stable archive construction."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_skill", ROOT / "scripts/package_skill.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_skill_discovery_metadata_and_agent_interface_are_valid(self):
        import yaml
        skill = ROOT / "java-modernize/SKILL.md"
        content = skill.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        metadata = yaml.safe_load(content.split("---\n", 2)[1])
        self.assertEqual(metadata["name"], skill.parent.name)
        self.assertRegex(metadata["name"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(metadata["name"]), 64)
        self.assertIsInstance(metadata["description"], str)
        self.assertTrue(metadata["description"].strip())
        self.assertLessEqual(len(metadata["description"]), 1024)
        interface = yaml.safe_load((skill.parent / "agents/openai.yaml").read_text())["interface"]
        self.assertIn("$" + metadata["name"], interface["default_prompt"])

    def test_stable_archive_and_manifest_cover_all_shipped_bytes(self):
        first, second = self.root / "first.zip", self.root / "second.zip"
        MODULE.package(first)
        MODULE.package(second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with ZipFile(first) as archive:
            self.assertIsNone(archive.testzip())
            manifest = json.loads(archive.read("java-modernize/PACKAGE-MANIFEST.json"))
            self.assertEqual(set(archive.namelist()), {"java-modernize/" + path for path in manifest["files"]} | {"java-modernize/PACKAGE-MANIFEST.json"})
            for name, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256(archive.read("java-modernize/" + name)).hexdigest(), digest)
                self.assertNotIn("__pycache__", name)
            for required in ("assets/enterprise-report.schema.json", "scripts/validate_report.py", "LICENSE", "THIRD_PARTY_NOTICES.md"):
                self.assertIn(required, manifest["files"])
        recorded = first.with_suffix(".zip.sha256").read_text().split()[0]
        self.assertEqual(recorded, hashlib.sha256(first.read_bytes()).hexdigest())

    def test_exported_licenses_match_repository_notices(self):
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            self.assertEqual((ROOT / name).read_bytes(), (ROOT / "java-modernize" / name).read_bytes())

    def test_local_documentation_links_exist(self):
        for path in ROOT.rglob("*.md"):
            if any(part in {".git", "dist", ".venv"} for part in path.parts):
                continue
            for destination in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if destination.startswith(("http:", "https:", "#", "/", "app:")):
                    continue
                target = path.parent / destination.split("#")[0]
                self.assertTrue(target.exists(), f"{path.relative_to(ROOT)} points to missing {destination}")

    def test_output_cannot_contaminate_skill_inputs(self):
        with self.assertRaises(ValueError):
            MODULE.package(ROOT / "java-modernize/generated.zip")


if __name__ == "__main__":
    unittest.main()
