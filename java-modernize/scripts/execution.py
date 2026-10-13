"""Verify collected execution records without rerunning any command."""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from snapshot import digest_file


def input_digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_execution(report, root, execution_id, *, kind, policy_hash, now, module=None, check=None, graph_artifact_ids=None):
    from validate_report import MAX_REPORT_BYTES, no_duplicates, reject_constant, timestamp, safe_path
    artifacts = {a["id"]: a for a in report["artifacts"]}
    errors = []
    def local_artifact(item):
        if not safe_path(item["path"]):
            raise ValueError("Unsafe execution artifact")
        path = root
        for part in Path(item["path"]).parts:
            path = path / part
            if path.is_symlink():
                raise ValueError("Symlink execution artifact")
        if digest_file(path) != item["sha256"]:
            raise ValueError("Changed execution artifact")
        return path
    try:
        artifact = artifacts[execution_id]
        if artifact.get("kind") != "execution":
            raise ValueError("Not an execution record")
        path = local_artifact(artifact)
        with path.open("rb") as source:
            raw = source.read(MAX_REPORT_BYTES + 1)
        if len(raw) > MAX_REPORT_BYTES:
            raise ValueError("Oversized execution record")
        record = json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=reject_constant)
        if record["schema_version"] != 1 or record["kind"] != kind or record["status"] != "passed" or type(record["exit_code"]) is not int or record["exit_code"] != 0 or record["timed_out"] is not False or record["problems"]:
            raise ValueError("Execution did not pass")
        started, finished = timestamp(record["started_at"]), timestamp(record["finished_at"])
        if started > finished or finished > timestamp(report["generated_at"]) or finished > now:
            raise ValueError("Invalid execution timestamps")
        from datetime import timedelta
        age = report["policy"]["evidence_max_age_days"]
        if age is None or now - finished > timedelta(days=age):
            raise ValueError("Stale execution")
        if record["policy_sha256"] != policy_hash or record["inputs_before_sha256"] != record["inputs_after_sha256"]:
            raise ValueError("Execution changed inputs or used another policy")
        if kind != "baseline" and record["inputs_after_sha256"] != input_digest(report["inputs_snapshot"]["files"]):
            raise ValueError("Execution used different project inputs")
        if module is not None and record["module"] != module:
            raise ValueError("Execution module mismatch")
        recorded = record["artifacts"]
        if not recorded or len({a["id"] for a in recorded}) != len(recorded):
            raise ValueError("Execution artifact set missing or duplicated")
        for item in recorded:
            if item != artifacts[item["id"]]:
                raise ValueError("Execution artifact reference mismatch")
            local_artifact(item)
        kinds = {a.get("kind") for a in recorded}
        if "log" not in kinds:
            raise ValueError("Execution log missing")
        if kind == "resolved-graph" and "resolved-graph" not in kinds:
            raise ValueError("Resolved graph missing")
        if graph_artifact_ids is not None and set(graph_artifact_ids) != {a["id"] for a in recorded if a.get("kind") == "resolved-graph"}:
            raise ValueError("Graph references disagree with execution")
        totals = record["test_summary"]
        if totals is not None:
            if "test-report" not in kinds or type(totals["executed"]) is not int or totals["executed"] <= 0 or totals["failures"] or totals["errors"]:
                raise ValueError("Test evidence is incomplete")
            from collect_evidence import read_test_reports
            xml_paths = [a["path"] for a in recorded if a.get("kind") == "test-report"]
            if read_test_reports(root, xml_paths, 0) != totals:
                raise ValueError("XML counters disagree with execution")
        if check is not None:
            if record["id"] != check["id"] or record["command"] != check["command"] or execution_id not in check["artifact_ids"] or not {a["id"] for a in recorded}.issubset(check["artifact_ids"]):
                raise ValueError("Check disagrees with execution")
            if kind in {"unit-tests", "integration-tests"}:
                totals = record["test_summary"]
                if "test-report" not in kinds or type(totals["executed"]) is not int or totals["executed"] <= 0 or totals["failures"] or totals["errors"] or totals["executed"] != check["tests_after"]:
                    raise ValueError("Test count disagrees with execution")
                if "tests_before" in check:
                    baseline_id = check.get("baseline_execution_artifact_id")
                    if not baseline_id:
                        raise ValueError("Baseline counts need collected execution evidence")
                    baseline_errors = verify_execution(report, root, baseline_id, kind="baseline", policy_hash=policy_hash, now=now)
                    if baseline_errors:
                        raise ValueError("Invalid baseline execution")
                    baseline_path = local_artifact(artifacts[baseline_id])
                    baseline = json.loads(baseline_path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates, parse_constant=reject_constant)
                    if baseline["test_summary"]["executed"] != check["tests_before"]:
                        raise ValueError("Baseline counts disagree with execution")
        for probe in record["tool_versions"]:
            if probe["exit_code"] != 0 or artifacts[probe["artifact_id"]].get("kind") != "tool-version":
                raise ValueError("Version probe is missing or failed")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, ET.ParseError):
        errors.append("/execution: missing, invalid, stale or contradictory process evidence")
    return errors
