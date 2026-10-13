"""Opt-in evidence capture against real Maven/Gradle builds and resolved graphs."""

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "java-modernize/scripts"))
sys.path.insert(0, str(ROOT / "scripts"))
from collect_evidence import collect
from execution import verify_execution
from run_migration_scenarios import Scenarios, parse_args
from validate_report import timestamp
import run_documents as runs


@unittest.skipUnless(os.environ.get("JAVA_MODERNIZE_EVIDENCE_E2E") == "1", "Enable the explicit build-evidence integration profile")
class NativeEvidenceTests(unittest.TestCase):
    def test_native_maven_and_gradle_evidence(self):
        args, _ = parse_args(["--case", "boot-same-java-patch", "--case", "gradle-groovy-catalog"])
        scenarios = Scenarios(args)
        scenarios.verify_tools(["boot-same-java-patch", "gradle-groovy-catalog"])
        projects = [(scenarios.copy("spring-boot", "maven-evidence"), False), (scenarios.copy("gradle-catalog", "gradle-evidence", "groovy"), True)]
        original_env = os.environ.copy()
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(original_env)))
        os.environ.update(scenarios.env(args.jdk21))
        results = []
        for project, gradle in projects:
            directory = project / ".java-modernize"
            directory.mkdir()
            policy = json.loads((ROOT / "java-modernize/assets/project-policy.example.json").read_text())
            policy_path = directory / "policy.json"
            policy_path.write_text(json.dumps(policy))
            manifest = runs.initialize(project, "native-evidence", {"app": "."})
            run_id = runs.read_json(manifest)["run_id"]
            if gradle:
                base = [args.gradle, "--no-daemon", "--console=plain", "--max-workers=2", "-Dorg.gradle.jvmargs=-Xmx768m -XX:ActiveProcessorCount=2"]
                command = base + ["clean", "test", "--rerun-tasks"]
                pattern = "build/test-results/test/TEST-*.xml"
                graph_command = base + ["dependencies"]
                graph_path = ".java-modernize/runs/" + run_id + "/evidence/graph/command.log"
            else:
                base = [args.maven, "-B", "-ntp", "-s", str(scenarios.settings), "-gs", str(scenarios.settings), "-Dmaven.repo.local=" + str(args.maven_repo)]
                command = base + ["clean", "verify"]
                pattern = "target/surefire-reports/TEST-*.xml"
                graph_command = base + ["org.apache.maven.plugins:maven-dependency-plugin:3.11.0:tree", "-DoutputType=json", "-DoutputFile=target/dependencies.json"]
                graph_path = "target/dependencies.json"
            result = collect(project, policy_path, "tests", "unit-tests", command, test_globs=[pattern], probes=[[str(Path(args.jdk21) / "bin/java"), "-version"]], run_id=run_id)
            self.assertEqual(result["record"]["status"], "passed", result["record"]["problems"])
            self.assertEqual(result["check"]["tests_after"], 1)
            graph = collect(project, policy_path, "graph", "resolved-graph", graph_command, graph=graph_path, run_id=run_id)
            self.assertEqual(graph["record"]["status"], "passed", graph["record"]["problems"])
            self.assertIn("junit-jupiter", (project / graph_path).read_text())
            # Verify actual evidence independently without rerunning the build.
            report = {"artifacts": result["artifacts"] + graph["artifacts"], "generated_at": graph["record"]["finished_at"], "policy": {"evidence_max_age_days": 7}, "inputs_snapshot": graph["inputs_snapshot"]}
            errors = verify_execution(report, project, result["check"]["execution_artifact_id"], kind="unit-tests", policy_hash=result["record"]["policy_sha256"], now=timestamp(report["generated_at"]), check=result["check"])
            self.assertEqual(errors, [])
            runs.checkpoint(manifest, {"app": policy_path})
            self.assertEqual(runs.resume(manifest, {"app": policy_path}), [])
            runs.render(manifest, check=True)
            results.append({"project": str(project), "run_id": run_id, "manifest": str(manifest), "build": "Gradle" if gradle else "Maven", "tests": result["check"]["tests_after"], "graph": graph_path, "tool_probes": len(result["record"]["tool_versions"])})
        output = ROOT / "dist/evidence-integration.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
