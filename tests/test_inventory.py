"""Observable invariants for the read-only helper, independent of build execution."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "java-modernize/scripts/inventory.py"
SPEC = importlib.util.spec_from_file_location("inventory", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative, content):
        file = self.root / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
        return file

    def test_multi_module_evidence_does_not_guess_inherited_targets(self):
        self.write("pom.xml", "<java.version>17</java.version>\n<maven.compiler.release>${java.version}</maven.compiler.release>")
        self.write("service/pom.xml", "<parent>\n<version>${revision}</version>\n</parent>")
        self.write("client/build.gradle.kts", "java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }\ntasks.withType<JavaCompile> { options.release.set(11) }")
        self.write("gradle/custom.versions.toml", "[versions]\njunit = 'example'\n[libraries]")
        result = MODULE.inventory(self.root)
        self.assertFalse(result["effective_versions_resolved"])
        self.assertEqual({item["path"] for item in result["files"]}, {
            "pom.xml", "service/pom.xml", "client/build.gradle.kts", "gradle/custom.versions.toml"
        })
        client = next(item for item in result["files"] if item["path"].startswith("client"))
        self.assertIn({"line": 1, "signal": "compiler-or-test-toolchain"}, client["evidence"])
        self.assertIn({"line": 2, "signal": "java-release-or-language"}, client["evidence"])
        self.assertNotIn("selected", result)

    def test_cli_never_executes_build_and_preserves_files(self):
        self.write("mvnw", "#!/bin/sh\ntouch build-was-executed\n")
        self.write("pom.xml", "<maven.compiler.release>17</maven.compiler.release>")
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        call = subprocess.run([sys.executable, str(SCRIPT), str(self.root)], capture_output=True, text=True, check=True)
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(json.loads(call.stdout)["scope"], "static-configuration-inventory")

    def test_cache_and_symlink_outputs_are_not_followed(self):
        self.write("target/pom.xml", "ignored")
        self.write(".git/pom.xml", "ignored")
        self.write("buildSrc/build.gradle.kts", "plugins { java }")
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "pom.xml").write_text("external", encoding="utf-8")
        project = self.root / "project"
        project.mkdir()
        try:
            (project / "pom.xml").symlink_to(outside / "pom.xml")
            (project / "linked-module").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation is unavailable on this platform")
        result = MODULE.inventory(project)
        self.assertEqual(result["files"], [])
        self.assertEqual(result["skipped"], [{"path": "pom.xml", "reason": "symlink"}])
        own = MODULE.inventory(self.root)
        paths = {item["path"] for item in own["files"]}
        self.assertNotIn("target/pom.xml", paths)
        self.assertNotIn(".git/pom.xml", paths)
        self.assertIn("buildSrc/build.gradle.kts", paths)

    def test_output_omits_configuration_values_and_secrets(self):
        self.write(".github/workflows/build.yml", "java-version: 17 # super-private-token\npassword: extremely-private\nuses: actions/setup-java@example")
        self.write("Dockerfile", "FROM private-registry.example/internal-build-image:17")
        rendered = json.dumps(MODULE.inventory(self.root))
        for value in ["super-private-token", "extremely-private", "private-registry.example", "setup-java"]:
            self.assertNotIn(value, rendered)
        self.assertIn("runtime-or-ci-java", rendered)
        self.assertIn("wrapper-or-image", rendered)

    def test_large_or_non_utf8_files_are_reported_not_silently_lost(self):
        self.write("pom.xml", "x" * 20)
        (self.root / "gradle.properties").write_bytes(b"\xff\xfe")
        result = MODULE.inventory(self.root, max_file_bytes=10)
        self.assertEqual(result["files"], [])
        reasons = {item["reason"] for item in result["skipped"]}
        self.assertEqual(reasons, {"size-limit", "unreadable-or-non-utf8"})

    def test_nonexistent_root_returns_nonzero(self):
        call = subprocess.run([sys.executable, str(SCRIPT), str(self.root / "missing")], capture_output=True, text=True)
        self.assertEqual(call.returncode, 2)
        self.assertEqual(call.stdout, "")

    def test_enterprise_build_sources_and_repository_signals(self):
        self.write("build-logic/src/main/kotlin/Conventions.kt", "repositories { exclusiveContent {} }")
        self.write("settings.gradle.kts", "dependencyResolutionManagement { repositoriesMode.set(FAIL_ON_PROJECT_REPOS) }")
        self.write(".mvn/extensions.xml", "<extensions/>")
        self.write("gradlew", "#!/bin/sh\nexit 99")
        result = MODULE.inventory(self.root)
        files = {item["path"]: item for item in result["files"]}
        self.assertEqual(files["build-logic/src/main/kotlin/Conventions.kt"]["category"], "build-convention-source")
        self.assertIn({"line": 1, "signal": "repository-or-trust"}, files["settings.gradle.kts"]["evidence"])
        self.assertEqual(files["gradlew"]["category"], "wrapper-launcher")

    def test_limits_and_exclusions_are_visible(self):
        self.write("a/pom.xml", "<project/>")
        self.write("b/pom.xml", "<project/>")
        self.write("vendor/pom.xml", "<project/>")
        limited = MODULE.inventory(self.root, max_configs=1)
        self.assertTrue(limited["discovery_truncated"])
        self.assertEqual(len(limited["files"]), 1)
        excluded = MODULE.inventory(self.root, excludes=["vendor"])
        self.assertFalse(excluded["discovery_truncated"])
        self.assertEqual({f["path"] for f in excluded["files"]}, {"a/pom.xml", "b/pom.xml"})
        self.assertIn({"path": "vendor", "reason": "requested-exclusion"}, excluded["excluded_directories"])

    def test_explicit_config_does_not_escape_root_or_follow_ancestors(self):
        self.write("build/custom.config", "maven.compiler.release=17")
        result = MODULE.inventory(self.root, include_configs=["build/custom.config"])
        self.assertEqual(result["files"][0]["path"], "build/custom.config")
        with self.assertRaises(ValueError):
            MODULE.inventory(self.root, include_configs=["../secret.config"])
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "secret.config").write_text("private", encoding="utf-8")
        try:
            (self.root / "linked").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation is unavailable on this platform")
        linked = MODULE.inventory(self.root, include_configs=["linked/secret.config"], excludes=["outside"])
        self.assertNotIn("linked/secret.config", {f["path"] for f in linked["files"]})
        self.assertIn({"path": "linked/secret.config", "reason": "symlink"}, linked["skipped"])


if __name__ == "__main__":
    unittest.main()
