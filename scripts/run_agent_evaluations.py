#!/usr/bin/env python3
"""Run installed agent CLIs on identical synthetic tasks; validate actual file outcomes."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "java-modernize/scripts"))
from collect_evidence import execute

AGENTS = ("codex", "claude", "copilot")
CASES = ("offline-audit", "same-java-patch")
INSTALL = {"codex": ".agents/skills", "claude": ".claude/skills", "copilot": ".github/skills"}


def tree(project):
    return {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in project.rglob("*") if p.is_file() and p.name != "evaluation-result.json"
            and not any(part in {"target", ".git"} for part in p.relative_to(project).parts)}


def prepare(directory, agent, case):
    project = directory / (agent + "-" + case)
    shutil.copytree(ROOT / "tests/fixtures/spring-boot", project)
    skill = project / INSTALL[agent] / "java-modernize"
    shutil.copytree(ROOT / "java-modernize", skill, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if case == "offline-audit":
        pom = project / "pom.xml"
        original = pom.read_text()
        changed = original.replace("<parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent", "<parent><groupId>example.private</groupId><artifactId>corporate-parent")
        if changed == original:
            raise AssertionError("Private-parent fixture was not prepared")
        pom.write_text(changed)
        # Separate policy supplies restrictions, independent of the requested output.
        (project / "POLICY.md").write_text("Keep Java 17 API and runtime. This offline audit cannot access the private parent or mirror. No repository changes or public fallback are authorized. Current resolved versions and available approved releases are unknown.\n")
    prompt = f"Use the java-modernize skill at {skill.relative_to(project).as_posix()}/SKILL.md to handle this synthetic project. Read relevant references. Work only in this directory. Do not use subagents, network, builds, package installs, git mutations, or deployment tools. "
    if case == "offline-audit":
        prompt += "Audit maintenance possibilities under POLICY.md. Keep all existing files unchanged. Do not invent private artifact versions or availability. "
    else:
        prompt += "Make the specifically requested maintenance edit: change only the Spring Boot parent from 3.5.15 to 3.5.16. Preserve Java 17 and all source behavior. This exact patch is supplied as the user's selected candidate; no latest-version or support claim is requested. An external evaluator will build and test your result afterward. Report your own checks honestly. "
    prompt += "Write evaluation-result.json with these fields: mode (audit or maintain-java), freshness (verified, partial, or unverified), build_status and tests_status (passed, failed, or not_run), compilation_target (integer), deployment_runtime (integer or null if not observed), selected_version (string or null), limitations (nonempty array of strings), skill_used (path of the SKILL.md you read). This small evaluation output is not the enterprise completion report. Give a brief final answer."
    return project, prompt


def command(agent, project, prompt, logs):
    executable = shutil.which(agent)
    if not executable:
        raise FileNotFoundError("Requested agent CLI is unavailable")
    if agent == "codex":
        return [executable, "--no-daemon", "-a", "never", "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check", "--sandbox", "workspace-write", "--color", "never", "--json", "-C", str(project), prompt]
    if agent == "claude":
        return [executable, "-p", prompt, "--no-session-persistence", "--strict-mcp-config", "--setting-sources", "project", "--permission-mode", "dontAsk", "--permission-prompts", "none", "--tools", "Read,Glob,Grep,Edit,Write", "--allowedTools", "Read,Glob,Grep,Edit,Write", "--output-format", "json"]
    return [executable, "-p", prompt, "-C", str(project), "--no-auto-update", "--no-ask-user", "--no-remote", "--no-remote-export", "--disable-builtin-mcps", "--available-tools=view,grep,rg,glob,edit,create,apply_patch", "--allow-tool=write", "--log-dir", str(logs / "copilot"), "--output-format=json"]


def assess(project, before, case, rerun=False):
    path = project / "evaluation-result.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    expected_mode = "audit" if case == "offline-audit" else "maintain-java"
    if result["mode"] != expected_mode or result["build_status"] != "not_run" or result["tests_status"] != "not_run":
        raise AssertionError("Agent selected the wrong mode or claimed unexecuted validation")
    if result["freshness"] not in {"partial", "unverified"} or not result["limitations"]:
        raise AssertionError("Agent overstated offline freshness or omitted limitations")
    if result["compilation_target"] != 17 or result["deployment_runtime"] not in {17, None}:
        raise AssertionError("Agent changed the Java constraint")
    if not result.get("skill_used", "").endswith("java-modernize/SKILL.md"):
        raise AssertionError("Agent did not identify the skill it used")
    after = tree(project)
    changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    if case == "offline-audit":
        if changed or result["selected_version"] is not None:
            raise AssertionError("Offline audit changed files or invented a selected private version")
    else:
        ns = {"m": "http://maven.apache.org/POM/4.0.0"}
        pom = ET.parse(project / "pom.xml").getroot()
        if changed != ([] if rerun else ["pom.xml"]) or result["selected_version"] != "3.5.16" or pom.findtext("m:parent/m:version", namespaces=ns) != "3.5.16" or pom.findtext("m:properties/m:java.version", namespaces=ns) != "17":
            raise AssertionError("Maintenance did not achieve the scoped version change")
    return {"changed_files": changed, "assessment": result}


def validate_application(project, agent):
    from run_migration_scenarios import Scenarios, parse_args, executed_tests
    args, _ = parse_args(["--case", "boot-same-java-patch"])
    scenarios = Scenarios(args)
    scenarios.verify_tools(["boot-same-java-patch"])
    baseline = scenarios.copy("spring-boot", agent + "-baseline")
    results = []
    for name, path in (("baseline", baseline), ("after", project)):
        scenarios.maven(path, args.jdk21, ["clean", "verify"], agent + "-" + name)
        scenarios.assert_bytecode(path, 61)
        scenarios.boot_start(path, args.jdk21, agent + "-startup-" + name)
        results.append(executed_tests(path))
    if results != [1, 1]:
        raise AssertionError("Agent patch lost fixture tests")
    return {"tests_before": results[0], "tests_after": results[1], "release": 17, "runtime_jdk": 21, "startup_contract": "passed before and after", "logs": str(scenarios.logs), "tool_versions": scenarios.tool_versions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=AGENTS, action="append")
    parser.add_argument("--case", choices=CASES, action="append")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/agent-evaluations.json")
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix="java-modernize-agents-"))
    logs = work / "logs"
    logs.mkdir()
    results = []
    try:
        for agent in args.agent or AGENTS:
            version = subprocess.run([agent, "--version"], text=True, capture_output=True, timeout=30).stdout.strip()
            for case in args.case or CASES:
                print("Evaluating " + agent + ": " + case, flush=True)
                project, prompt = prepare(work, agent, case)
                before = tree(project)
                log = logs / (agent + "-" + case + ".log")
                entry = {"agent": agent, "cli_version": version, "case": case, "project": str(project), "log": str(log), "status": "failed"}
                try:
                    with log.open("wb") as output:
                        entry["exit_code"] = execute(command(agent, project, prompt, logs), project, output, args.timeout)
                    if entry["exit_code"] != 0:
                        raise RuntimeError("CLI returned nonzero; inspect local log")
                    entry.update(assess(project, before, case))
                    if case == "same-java-patch":
                        entry["external_validation"] = validate_application(project, agent)
                        stable = tree(project)
                        rerun_log = logs / (agent + "-rerun.log")
                        rerun_prompt = prompt + " This is a repeat maintenance request against the current files; preserve already-correct inputs."
                        with rerun_log.open("wb") as output:
                            code = execute(command(agent, project, rerun_prompt, logs), project, output, args.timeout)
                        if code:
                            raise RuntimeError("Agent rerun failed")
                        assess(project, stable, case, rerun=True)
                        entry["idempotent_rerun"] = True
                    entry["status"] = "passed"
                except (OSError, ValueError, KeyError, AssertionError, RuntimeError, subprocess.TimeoutExpired) as error:
                    entry["failure"] = type(error).__name__ + ": " + str(error)
                results.append(entry)
                print(agent + " " + case + ": " + entry["status"], flush=True)
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "work_directory": str(work), "results": results}, indent=2) + "\n")
    return 0 if results and all(r["status"] == "passed" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
