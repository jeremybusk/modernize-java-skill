#!/usr/bin/env python3
"""Execute one explicitly supplied command and record local evidence; never read commands from reports."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

from policy import load_policy
from snapshot import capture, digest_file
from validate_report import safe_path
from run_documents import RUN_ID, local_path


MAX_XML_BYTES = 16 * 1024 * 1024


def input_digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def local_file(root, relative):
    if not safe_path(relative):
        raise ValueError("Unsafe evidence path")
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("Symlink evidence path")
    if not path.is_file():
        raise ValueError("Missing evidence file")
    return path


def read_test_reports(root, paths, started_ns):
    totals = {"executed": 0, "skipped": 0, "failures": 0, "errors": 0}
    if not paths:
        raise ValueError("No test XML matched the requested scope")
    for relative in paths:
        path = local_file(root, relative)
        if path.stat().st_mtime_ns < started_ns:
            raise ValueError("Stale test report; force tests to execute in this run")
        with path.open("rb") as source:
            raw = source.read(MAX_XML_BYTES + 1)
        if len(raw) > MAX_XML_BYTES or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("Unbounded or unsupported XML")
        node = ET.fromstring(raw)
        suites = [node] if node.tag == "testsuite" else list(node) if node.tag == "testsuites" else []
        if not suites or any(s.tag != "testsuite" for s in suites):
            raise ValueError("Unsupported test XML shape")
        for suite in suites:
            counts = {key: int(suite.attrib[key]) for key in ("tests", "skipped", "failures", "errors")}
            if any(n < 0 for n in counts.values()) or counts["skipped"] + counts["failures"] + counts["errors"] > counts["tests"]:
                raise ValueError("Inconsistent test counters")
            totals["executed"] += counts["tests"] - counts["skipped"]
            for key in ("skipped", "failures", "errors"):
                totals[key] += counts[key]
    return totals


def display_argv(argv):
    # Logs stay local; do not copy credentials in command arguments into a JSON report.
    result, hide_next = [], False
    for arg in argv:
        if hide_next:
            result.append("<redacted>")
            hide_next = False
            continue
        if re.search(r"(?i)(password|passwd|secret|token|credential|api[-_]?key|authorization)", arg):
            if "=" in arg:
                result.append(arg.split("=", 1)[0] + "=<redacted>")
            else:
                result.append(arg)
                hide_next = True
            continue
        arg = re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1<redacted>@", arg)
        result.append(arg)
    return shlex.join(result)


def execute(argv, root, output, timeout):
    process = subprocess.Popen(argv, cwd=root, stdout=output, stderr=subprocess.STDOUT, shell=False, start_new_session=os.name == "posix")
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=10)
        raise


def version_probes(argv):
    name = Path(argv[0]).name.lower()
    if name in {"java", "java.exe", "javac", "javac.exe", "mvn", "mvn.cmd", "mvnw", "mvnw.cmd"}:
        return [[argv[0], "-version"]]
    if name in {"gradle", "gradle.bat", "gradlew", "gradlew.bat"}:
        return [[argv[0], "--version"]]
    if re.fullmatch(r"python(?:[0-9.]+)?(?:\.exe)?", name):
        return [[argv[0], "--version"]]
    return []


def collect(root, policy_path, check_id, kind, argv, *, test_globs=(), graph=None, module=".", timeout=900, probes=(), run_id=None):
    root = Path(root).resolve(strict=True)
    policy, policy_bytes = load_policy(policy_path)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", check_id) or not argv or timeout < 1:
        raise ValueError("Invalid invocation")
    if ".java-modernize" not in policy["input_scope"]["excluded_dirs"]:
        raise ValueError("Policy must exclude the local evidence directory")
    if module not in {m["path"] for m in policy["modules"]} or any(not safe_path(pattern) for pattern in test_globs):
        raise ValueError("Module or report scope is outside policy")
    if run_id is not None and (not re.fullmatch(RUN_ID, run_id) or len(run_id) > 100):
        raise ValueError("Invalid run ID")
    relative = ".java-modernize/" + ("runs/" + run_id + "/evidence/" if run_id else "") + check_id
    directory = local_path(root, relative)
    # One record per execution; never silently overwrite old validation evidence.
    directory.mkdir(parents=True, exist_ok=False)
    artifacts = []
    def artifact(path, artifact_kind):
        relative = path.relative_to(root).as_posix()
        local_file(root, relative)
        item = {"id": check_id + "-" + str(len(artifacts)), "path": relative, "sha256": digest_file(path), "kind": artifact_kind}
        artifacts.append(item)
        return item
    before = capture(root, policy["input_scope"]["excluded_dirs"])
    started_ns = time.time_ns()
    started = utc_now()
    log = directory / "command.log"
    returncode, timed_out = None, False
    with log.open("wb") as output:
        try:
            returncode = execute(argv, root, output, timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        except OSError:
            returncode = 127
    artifact(log, "log")
    after = capture(root, policy["input_scope"]["excluded_dirs"])
    test_summary, problems = None, []
    if kind in {"unit-tests", "integration-tests"} or (kind == "baseline" and test_globs):
        paths = sorted({p.relative_to(root).as_posix() for pattern in test_globs for p in root.glob(pattern)})
        try:
            test_summary = read_test_reports(root, paths, started_ns)
            reports = directory / "test-reports"
            reports.mkdir()
            for number, path in enumerate(paths):
                saved = reports / (str(number) + ".xml")
                shutil.copyfile(local_file(root, path), saved)
                artifact(saved, "test-report")
            if test_summary["executed"] == 0 or test_summary["failures"] or test_summary["errors"]:
                problems.append("Test reports contain zero executed tests or failures/errors")
        except (OSError, ValueError, ET.ParseError):
            problems.append("Test reports are missing, stale, unsafe or invalid")
    if kind == "resolved-graph":
        try:
            graph_file = local_file(root, graph)
            if graph_file.stat().st_mtime_ns < started_ns or not graph_file.stat().st_size:
                raise ValueError("Graph is stale or empty")
            saved = directory / "resolved-graph.txt"
            shutil.copyfile(graph_file, saved)
            artifact(saved, "resolved-graph")
        except (OSError, TypeError, ValueError):
            problems.append("Resolved graph output is missing, empty, stale or unsafe")
    version_results = []
    all_probes = version_probes(argv) + list(probes)
    for number, probe in enumerate(all_probes):
        path = directory / ("tool-" + str(number) + ".log")
        try:
            with path.open("wb") as output:
                code = execute(probe, root, output, min(timeout, 60))
            entry = artifact(path, "tool-version")
            executable = shutil.which(probe[0])
            if (root / probe[0]).is_file():
                executable = str(root / probe[0])
            version_results.append({"command": display_argv(probe), "exit_code": code, "artifact_id": entry["id"], "executable_sha256": digest_file(Path(executable)) if executable else None})
            if code:
                problems.append("A requested tool-version probe failed")
        except (OSError, subprocess.TimeoutExpired):
            problems.append("A requested tool-version probe could not execute")
    after = capture(root, policy["input_scope"]["excluded_dirs"])
    if before != after:
        problems.append("Validation command changed project inputs")
    passed = returncode == 0 and not timed_out and not problems
    record = {"schema_version": 1, "id": check_id, "kind": kind, "module": module, "started_at": started, "finished_at": utc_now(), "command": display_argv(argv), "exit_code": returncode, "timed_out": timed_out, "status": "passed" if passed else "failed", "policy_sha256": hashlib.sha256(policy_bytes).hexdigest(), "inputs_before_sha256": input_digest(before), "inputs_after_sha256": input_digest(after), "test_summary": test_summary, "tool_versions": version_results, "artifacts": artifacts.copy(), "problems": problems}
    path = directory / "execution.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    execution = artifact(path, "execution")
    check = {"id": check_id, "kind": kind, "required": True, "status": record["status"], "command": record["command"], "environment": "Recorded local process; inspect execution and tool-version artifacts", "reason": None if passed else "Process failed or evidence checks failed; inspect local execution record", "artifact_ids": [a["id"] for a in artifacts], "execution_artifact_id": execution["id"]}
    if test_summary is not None:
        check["tests_after"] = test_summary["executed"]
    graphs = [{"module": module, "artifact_ids": [a["id"] for a in artifacts if a["kind"] == "resolved-graph"], "execution_artifact_id": execution["id"]}] if kind == "resolved-graph" else []
    return {"record": record, "check": check, "artifacts": artifacts, "inputs_snapshot": {"captured_at": record["finished_at"], "files": after, "graphs": graphs}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--run-id", help="Timestamped run ID; stores evidence within this repository's matching run directory")
    parser.add_argument("--kind", required=True, choices=["baseline", "build", "unit-tests", "integration-tests", "api", "contract", "startup", "security", "performance", "other", "resolved-graph"])
    parser.add_argument("--test-glob", action="append", default=[])
    parser.add_argument("--graph", help="Project-relative resolved graph output written by this command")
    parser.add_argument("--module", default=".", help="Module covered by this execution, matching project policy")
    parser.add_argument("--probe-json", action="append", default=[], help="Explicit version-probe argument array, e.g. '[\"java\",\"-version\"]'")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        probes = [json.loads(value) for value in args.probe_json]
        if any(not isinstance(p, list) or not p or any(not isinstance(a, str) or not a for a in p) for p in probes):
            raise ValueError("Invalid version probe")
        result = collect(args.project, args.policy, args.id, args.kind, argv, test_globs=args.test_glob, graph=args.graph, module=args.module, timeout=args.timeout, probes=probes, run_id=args.run_id)
    except (OSError, ValueError, TypeError, UnicodeError):
        parser.exit(2, "Cannot collect evidence; check explicit command, policy and local output scope\n")
    # Graph executions are input evidence, not ordinary checks in the report schema.
    print(json.dumps({key: value for key, value in result.items() if key != "record" and (key != "check" or args.kind != "resolved-graph")}, indent=2))
    return 0 if result["record"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
