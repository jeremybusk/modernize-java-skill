#!/usr/bin/env python3
"""Execute complete migrations of controlled fixtures, never a user's application."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
CASES = ("java8-to25-reactor", "boot-same-java-patch", "boot-major", "gradle-groovy-catalog", "gradle-kotlin-catalog")
REWRITE_PLUGIN = "org.openrewrite.maven:rewrite-maven-plugin:6.46.1:run"
JAVA_RECIPE = "org.openrewrite.recipe:rewrite-migrate-java:3.42.1"
SPRING_RECIPE = "org.openrewrite.recipe:rewrite-spring:6.37.1"


def fingerprint(project):
    return {
        str(p.relative_to(project).as_posix()): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(project.rglob("*"))
        if p.is_file() and not any(part in {"target", "build", ".gradle", ".git"} for part in p.relative_to(project).parts)
    }


def executed_tests(project, gradle=False):
    pattern = "**/build/test-results/test/TEST-*.xml" if gradle else "**/target/surefire-reports/TEST-*.xml"
    total = 0
    reports = list(project.glob(pattern))
    if not reports:
        raise AssertionError("No test reports were generated")
    for report in reports:
        suite = ET.parse(report).getroot()
        tests, skipped = int(suite.get("tests", 0)), int(suite.get("skipped", 0))
        if int(suite.get("failures", 0)) or int(suite.get("errors", 0)):
            raise AssertionError("Fixture test failures were reported")
        total += tests - skipped
    if total < 1:
        raise AssertionError("Zero executed tests is not a successful migration")
    return total


class Scenarios:
    def __init__(self, args):
        self.args = args
        self.work = Path(tempfile.mkdtemp(prefix="java-modernize-e2e-", dir=args.work_root))
        self.logs = self.work / "logs"
        self.logs.mkdir()
        self.settings = self.work / "settings.xml"
        self.settings.write_text('<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0"/>', encoding="utf-8")
        self.commands = []
        self.tool_versions = {}

    def verify_tools(self, selected):
        homes = {21: self.args.jdk21}
        if "java8-to25-reactor" in selected:
            homes.update({8: self.args.jdk8, 25: self.args.jdk25})
        for expected, home in homes.items():
            output = self.command([str(Path(home) / "bin/java"), "-version"], self.work, home, "jdk" + str(expected) + "-version")
            match = re.search(r'version\s+"([^\"]+)"', output)
            if not match:
                raise AssertionError("Could not identify the actual JDK version")
            parts = match.group(1).split(".")
            feature = int(parts[1]) if parts[0] == "1" else int(parts[0])
            if feature != expected:
                raise AssertionError("Toolchain argument does not contain the claimed JDK")
            self.tool_versions["jdk" + str(expected)] = match.group(1)
        if any(name.startswith("gradle-") for name in selected):
            output = self.command([self.args.gradle, "--version"], self.work, self.args.jdk21, "gradle-version")
            match = re.search(r"Gradle ([0-9.]+)", output)
            if not match or match.group(1) != "8.14.3":
                raise AssertionError("These pinned scenarios require Gradle 8.14.3")
            self.tool_versions["gradle"] = match.group(1)
        if any(not name.startswith("gradle-") for name in selected):
            output = self.command([self.args.maven, "-version"], self.work, self.args.jdk21, "maven-version")
            match = re.search(r"Apache Maven ([0-9.]+)", output)
            if not match:
                raise AssertionError("Could not identify Maven version")
            self.tool_versions["maven"] = match.group(1)

    def env(self, jdk):
        env = os.environ.copy()
        for key in ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "MAVEN_ARGS", "MAVEN_CONFIG", "GRADLE_OPTS"):
            env.pop(key, None)
        for key in list(env):
            if key.startswith(("SPRING_", "SERVER_", "MANAGEMENT_", "LOGGING_")):
                env.pop(key)
        env["MAVEN_SKIP_RC"] = "1"
        env["JAVA_HOME"] = str(Path(jdk).resolve())
        env["PATH"] = str(Path(jdk) / "bin") + os.pathsep + env.get("PATH", "")
        env["MAVEN_OPTS"] = "-Xmx1024m -XX:ActiveProcessorCount=2"
        env["GRADLE_USER_HOME"] = str(Path(self.args.gradle_home).resolve())
        env["JAVA_MODERNIZE_M2_REPO"] = str(Path(self.args.maven_repo).resolve())
        return env

    def command(self, command, project, jdk, label, timeout=900):
        print(label, flush=True)
        log = self.logs / (label + ".log")
        with log.open("w", encoding="utf-8") as output:
            result = subprocess.run(command, cwd=project, env=self.env(jdk), stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        self.commands.append({"label": label, "command": command, "jdk_home": str(jdk), "exit_code": result.returncode, "log": str(log)})
        if result.returncode:
            tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-45:]
            raise RuntimeError(label + " failed; " + str(log) + "\n" + "\n".join(tail))
        return log.read_text(encoding="utf-8", errors="replace")

    def maven(self, project, jdk, goals, label):
        command = [self.args.maven, "-B", "-ntp", "-s", str(self.settings), "-gs", str(self.settings), "-Dmaven.repo.local=" + str(Path(self.args.maven_repo).resolve())]
        if self.args.offline:
            command.append("-o")
        return self.command(command + goals, project, jdk, label)

    def rewrite(self, project, jdk, recipe, artifact, label, config=None):
        args = [REWRITE_PLUGIN, "-Drewrite.activeRecipes=" + recipe, "-Drewrite.failOnInvalidActiveRecipes=true", "-Drewrite.exportDatatables=true"]
        if artifact:
            args.append("-Drewrite.recipeArtifactCoordinates=" + artifact)
        if config:
            args.append("-Drewrite.configLocation=" + str(config))
        return self.maven(project, jdk, args, label)

    def stabilize(self, project, jdk, recipe, artifact, label, config=None):
        # New source/API attribution after a JDK change can enable another transform.
        # Bound the reparse/apply loop, then validate and separately test a no-op rerun.
        for number in range(1, 5):
            before = fingerprint(project)
            self.rewrite(project, jdk, recipe, artifact, label + "-" + str(number), config)
            if before == fingerprint(project):
                return number
        raise AssertionError("Recipe did not stabilize within four reviewed fixture passes")

    def copy(self, fixture, name, dsl=None):
        project = self.work / name
        def ignore(directory, names):
            if not dsl:
                return []
            suffix = ".gradle.kts" if dsl == "groovy" else ".gradle"
            return [n for n in names if n.endswith(suffix)]
        shutil.copytree(FIXTURES / fixture, project, ignore=ignore)
        return project

    def assert_bytecode(self, project, expected, gradle=False):
        pattern = "**/build/classes/java/main/**/*.class" if gradle else "**/target/classes/**/*.class"
        classes = list(project.glob(pattern))
        if not classes:
            raise AssertionError("No production bytecode was generated")
        if any(struct.unpack(">H", p.read_bytes()[6:8])[0] != expected for p in classes):
            raise AssertionError("Compilation target differs from the selected Java target")

    def boot_start(self, project, jdk, label):
        jar = project / "target/boot-app-1.0.0.jar"
        log = self.logs / (label + ".log")
        command = [str(Path(jdk) / "bin/java"), "-Xmx384m", "-jar", str(jar), "--server.address=127.0.0.1", "--server.port=0"]
        with log.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(command, cwd=project, env=self.env(jdk), stdout=output, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 90
                port = None
                while time.monotonic() < deadline:
                    text = log.read_text(encoding="utf-8", errors="replace")
                    match = re.search(r"Tomcat started on port (\d+)", text)
                    if match:
                        port = int(match.group(1))
                        break
                    if process.poll() is not None:
                        raise RuntimeError("Application failed during startup: " + str(log))
                    time.sleep(0.2)
                if port is None:
                    raise RuntimeError("Application startup timed out: " + str(log))
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open("http://127.0.0.1:" + str(port) + "/hello", timeout=10) as response:
                    body = json.load(response)
                if body != {"message": "hello"}:
                    raise AssertionError("HTTP wire contract changed")
                self.commands.append({"label": label, "command": command, "jdk_home": str(jdk), "exit_code": 0, "log": str(log), "http_contract": body})
            finally:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

    def java_reactor(self):
        project = self.copy("maven-java8", "java8-to25-reactor")
        self.maven(project, self.args.jdk8, ["clean", "install"], "reactor-baseline")
        before = executed_tests(project)
        self.assert_bytecode(project, 52)
        jars = [project / "app/target/app-1.0.0.jar", project / "core/target/core-1.0.0.jar"]
        def startup(jdk, label):
            output = self.command([str(Path(jdk) / "bin/java"), "-cp", os.pathsep.join(str(p) for p in jars), "example.Main"], project, jdk, label)
            if "MIGRATION_OK" not in output:
                raise AssertionError("Reactor application did not preserve startup contract")
        startup(self.args.jdk8, "reactor-startup-before")
        baseline = fingerprint(project)
        passes = self.stabilize(project, self.args.jdk25, "org.openrewrite.java.migrate.UpgradeToJava25", JAVA_RECIPE, "reactor-migrate")
        if baseline == fingerprint(project):
            raise AssertionError("Java migration made no configuration/source changes")
        self.maven(project, self.args.jdk25, ["clean", "install"], "reactor-after")
        after = executed_tests(project)
        self.assert_bytecode(project, 69)
        startup(self.args.jdk25, "reactor-startup-after")
        changed = fingerprint(project)
        self.rewrite(project, self.args.jdk25, "org.openrewrite.java.migrate.UpgradeToJava25", JAVA_RECIPE, "reactor-rerun")
        if changed != fingerprint(project):
            raise AssertionError("Second Java migration changed tracked fixture inputs")
        if after != before:
            raise AssertionError("Reactor migration changed executed test count")
        return {"case": "java8-to25-reactor", "tests_before": before, "tests_after": after, "baseline_jdk": 8, "after_jdk": 25, "stabilization_passes": passes, "idempotent": True, "inputs_after": changed}

    def spring(self, major):
        name = "boot-major" if major else "boot-same-java-patch"
        project = self.copy("spring-boot", name)
        pom = project / "pom.xml"
        if major:
            pom.write_text(pom.read_text().replace("3.5.15", "3.5.16"), encoding="utf-8")
        self.maven(project, self.args.jdk21, ["clean", "verify"], name + "-baseline")
        before = executed_tests(project)
        self.assert_bytecode(project, 61)
        self.boot_start(project, self.args.jdk21, name + "-startup-before")
        config = project / "rewrite.yml"
        if major:
            recipe, artifact = "org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0", SPRING_RECIPE
        else:
            config.write_text('''type: specs.openrewrite.org/v1beta/recipe
name: example.PatchBoot
displayName: Selected Boot maintenance patch
description: Update the fixture parent to the verified patch without changing Java.
recipeList:
  - org.openrewrite.maven.UpgradeParentVersion:
      groupId: org.springframework.boot
      artifactId: spring-boot-starter-parent
      newVersion: "3.5.16"
''', encoding="utf-8")
            recipe, artifact = "example.PatchBoot", None
        baseline = fingerprint(project)
        passes = self.stabilize(project, self.args.jdk21, recipe, artifact, name + "-migrate", config if not major else None)
        if baseline == fingerprint(project):
            raise AssertionError("Framework migration made no changes")
        self.maven(project, self.args.jdk21, ["clean", "verify"], name + "-after")
        after = executed_tests(project)
        self.assert_bytecode(project, 61)
        self.boot_start(project, self.args.jdk21, name + "-startup-after")
        ns = {"m": "http://maven.apache.org/POM/4.0.0"}
        selected = ET.parse(pom).getroot().findtext("m:parent/m:version", namespaces=ns)
        if (major and not selected.startswith("4.0.")) or (not major and selected != "3.5.16"):
            raise AssertionError("Framework target was not met")
        if major:
            source = (project / "src/test/java/example/ApplicationTest.java").read_text()
            if "@MockBean" in source or "@MockitoBean" not in source:
                raise AssertionError("Framework test API was not migrated")
        changed = fingerprint(project)
        self.rewrite(project, self.args.jdk21, recipe, artifact, name + "-rerun", config if not major else None)
        if changed != fingerprint(project) or before != after:
            raise AssertionError("Framework migration is not stable or lost tests")
        return {"case": name, "selected_boot": selected, "release_before": 17, "release_after": 17, "runtime_jdk": 21, "stabilization_passes": passes, "tests_before": before, "tests_after": after, "idempotent": True, "inputs_after": changed}

    def gradle(self, dsl):
        name = "gradle-" + dsl + "-catalog"
        project = self.copy("gradle-catalog", name, dsl)
        base = [self.args.gradle, "--no-daemon", "--console=plain", "--max-workers=2", "-Dorg.gradle.jvmargs=-Xmx768m -XX:ActiveProcessorCount=2"]
        if self.args.offline:
            base.append("--offline")
        def build(label):
            self.command(base + ["clean", "build", "--write-locks"], project, self.args.jdk21, label)
            self.assert_bytecode(project, 61, gradle=True)
            return executed_tests(project, gradle=True)
        before = build(name + "-baseline")
        output = self.command(base + ["run"], project, self.args.jdk21, name + "-startup-before")
        if "MIGRATION_OK" not in output:
            raise AssertionError("Gradle baseline application startup failed")
        initial = fingerprint(project)
        def migrate():
            catalog = project / "gradle/libs.versions.toml"
            text = catalog.read_text()
            catalog.write_text(text.replace('junit = "5.11.4"', 'junit = "5.14.4"'), encoding="utf-8")
        migrate()
        after = build(name + "-after")
        locks = project / "gradle.lockfile"
        if not locks.is_file() or "org.junit.jupiter:junit-jupiter:5.14.4" not in locks.read_text():
            raise AssertionError("Gradle locks do not reflect the selected managed set")
        output = self.command(base + ["run"], project, self.args.jdk21, name + "-startup")
        if "MIGRATION_OK" not in output:
            raise AssertionError("Gradle application startup failed")
        changed = fingerprint(project)
        if changed == initial:
            raise AssertionError("Catalog maintenance did not change the selected version")
        migrate()
        rerun_tests = build(name + "-rerun")
        if changed != fingerprint(project) or before != after or after != rerun_tests:
            raise AssertionError("Catalog maintenance is not idempotent or lost tests")
        return {"case": name, "selected_junit": "5.14.4", "release_before": 17, "release_after": 17, "runtime_jdk": 21, "tests_before": before, "tests_after": after, "idempotent": True, "inputs_after": changed, "migration_method": "scoped manual catalog edit and native lock regeneration"}

    def run(self, selected):
        results = []
        operations = {"java8-to25-reactor": self.java_reactor, "boot-same-java-patch": lambda: self.spring(False), "boot-major": lambda: self.spring(True), "gradle-groovy-catalog": lambda: self.gradle("groovy"), "gradle-kotlin-catalog": lambda: self.gradle("kotlin")}
        try:
            self.verify_tools(selected)
            for name in selected:
                print("Starting " + name, flush=True)
                results.append(operations[name]())
        finally:
            summary = {"generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "work_directory": str(self.work), "tool_versions": self.tool_versions, "results": results, "commands": self.commands}
            self.args.output.parent.mkdir(parents=True, exist_ok=True)
            self.args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        return summary


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, action="append")
    parser.add_argument("--jdk8", default=os.environ.get("JAVA_MODERNIZE_JDK8"))
    parser.add_argument("--jdk25", default=os.environ.get("JAVA_MODERNIZE_JDK25"))
    parser.add_argument("--jdk21", default=os.environ.get("JAVA_MODERNIZE_JDK21", "/usr/lib/jvm/java-21-openjdk-amd64"))
    parser.add_argument("--maven", default=os.environ.get("JAVA_MODERNIZE_MAVEN", shutil.which("mvn")))
    parser.add_argument("--gradle", default=os.environ.get("JAVA_MODERNIZE_GRADLE", shutil.which("gradle")))
    parser.add_argument("--maven-repo", default=os.environ.get("JAVA_MODERNIZE_M2_REPO", "/tmp/java-modernize-m2"))
    parser.add_argument("--gradle-home", default=os.environ.get("JAVA_MODERNIZE_GRADLE_HOME", "/tmp/java-modernize-gradle"))
    parser.add_argument("--work-root", default=None)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/integration-summary.json")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    selected = args.case or CASES
    if "java8-to25-reactor" in selected and (not args.jdk8 or not args.jdk25):
        parser.error("Java 8 and 25 toolchain homes are required for the runtime migration")
    if any(name.startswith("gradle-") for name in selected) and not args.gradle:
        parser.error("A selected Gradle executable is required")
    if any(not name.startswith("gradle-") for name in selected) and not args.maven:
        parser.error("A Maven executable is required")
    return args, selected


def main():
    args, selected = parse_args()
    summary = Scenarios(args).run(selected)
    print("Passed " + str(len(summary["results"])) + " complete migration scenarios; " + str(args.output), flush=True)


if __name__ == "__main__":
    main()
