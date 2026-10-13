#!/usr/bin/env python3
"""Validate report shape, consistency and optional local artifact hashes. No builds/network."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

from snapshot import capture


SCHEMA = Path(__file__).resolve().parents[1] / "assets/enterprise-report.schema.json"
MAX_REPORT_BYTES = 4 * 1024 * 1024


def timestamp(value):
    # No optional jsonschema format dependencies: our contract explicitly uses UTC.
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value
    ):
        raise ValueError("Expected a UTC timestamp")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def safe_path(value):
    path = PurePosixPath(value)
    return bool(value) and "\\" not in value and not path.is_absolute() and ".." not in path.parts and ":" not in value and "\x00" not in value


def unique_ids(items, location, errors):
    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        errors.append(location + ": duplicate identifiers")
    return set(ids)


def validate(report, project_root=None, *, require_complete=False, now=None, project_policy=None, policy_sha256=None):
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        raise RuntimeError("Report validation requires pre-provisioned jsonschema 4.x") from None
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    formats = FormatChecker()

    @formats.checks("date-time", raises=(ValueError, TypeError))
    def valid_timestamp(value):
        timestamp(value)
        return True

    errors = []
    for error in Draft202012Validator(schema, format_checker=formats).iter_errors(report):
        # Do not print jsonschema's message: it can embed arbitrary input/credentials.
        location = "/" + "/".join(str(part) for part in error.absolute_path)
        errors.append(location + ": schema violation (" + error.validator + ")")
    if errors:
        return sorted(errors)

    generated = timestamp(report["generated_at"])
    complete = report["status"] == "complete" and report["mode"] != "audit"
    if project_policy is not None:
        from policy import validate_policy
        policy_errors = validate_policy(project_policy)
        if policy_errors:
            return policy_errors
    if require_complete and complete:
        if project_policy is None:
            errors.append("/policy: completion gate requires an independent project policy")
        else:
            if not policy_sha256 or report.get("policy_binding", {}).get("sha256") != policy_sha256:
                errors.append("/policy_binding: policy bytes differ from reviewed report binding")
            declared = report["policy"]
            if any(declared[key] != project_policy[key] for key in ("source", "evidence_max_age_days", "require_supported_updates")) or report["mode"] != project_policy["mode"]:
                errors.append("/policy: report contradicts independent project policy")
            modules = {m["path"]: m for m in report["modules"]}
            if set(modules) != {m["path"] for m in project_policy["modules"]}:
                errors.append("/policy/modules: report omits or adds module scope")
            for m in project_policy["modules"]:
                actual = modules.get(m["path"])
                if actual is None:
                    continue
                if any(actual["after"][role] != target for role, target in m["targets"].items()):
                    errors.append("/policy/modules: required Java target not achieved")
                for role in m["preserve"]:
                    if actual["before"][role] is None or actual["before"][role] != actual["after"][role]:
                        errors.append("/policy/modules: required preserved Java role changed or unknown")
            components = {c["id"]: c for c in report["components"]}
            if set(components) != {c["id"] for c in project_policy["components"]}:
                errors.append("/policy/components: report omits or adds assessment scope")
            for c in project_policy["components"]:
                actual = components.get(c["id"])
                if actual is None:
                    continue
                if actual["owner"] != c["owner"] or actual["action"] not in c["allowed_actions"] or (actual["action"] != "defer" and actual["selected"] not in c["selected_versions"]):
                    errors.append("/policy/components: owner, action or selected version violates project policy")
            checks = {c["id"]: c for c in report["checks"]}
            for c in project_policy["checks"]:
                actual = checks.get(c["id"])
                if actual is None or actual["kind"] != c["kind"] or actual["status"] not in c["allowed_statuses"]:
                    errors.append("/policy/checks: required check is missing, mismatched or unsuccessful")
    validation_time = now or datetime.now(timezone.utc)
    age_origin = validation_time if require_complete else generated
    if require_complete and complete:
        if generated > validation_time:
            errors.append("/generated_at: report is later than validation time")
        if report["policy"]["evidence_max_age_days"] is None:
            errors.append("/policy: completion needs a bounded evidence age")
    artifact_ids = unique_ids(report["artifacts"], "/artifacts", errors)
    unique_ids(report["components"], "/components", errors)
    unique_ids(report["checks"], "/checks", errors)
    module_paths = [module["path"] for module in report["modules"]]
    if len(module_paths) != len(set(module_paths)):
        errors.append("/modules: duplicate module paths")
    for i, module in enumerate(report["modules"]):
        if not safe_path(module["path"]):
            errors.append(f"/modules/{i}/path: unsafe project-relative path")
        if complete:
            for role, target in module.get("targets", {}).items():
                if module["after"][role] != target:
                    errors.append(f"/modules/{i}/{role}: requested target not achieved")
        preserved = set(module["preserve"])
        if report["mode"] in {"maintain-java", "modernize-code"}:
            preserved.update({"compilation_target", "deployment_runtime"})
        for role in preserved:
            before, after = module["before"][role], module["after"][role]
            if before is not None and after is not None and before != after:
                errors.append(f"/modules/{i}/{role}: violates preserved Java target")
            if complete and (before is None or after is None):
                errors.append(f"/modules/{i}/{role}: preservation is unverified")
        if complete and any(module["after"][role] is None for role in ("compilation_target", "deployment_runtime")):
            errors.append(f"/modules/{i}: complete implementation needs API and runtime targets")

    if report["freshness"] == "verified":
        age = report["policy"]["evidence_max_age_days"]
        for i, component in enumerate(report["components"]):
            if component["action"] == "defer":
                continue
            if component["current"] is None:
                errors.append(f"/components/{i}: verified freshness needs the observed current version")
            kinds = {e["kind"] for e in component["evidence"]}
            if not {"publication", "compatibility", "availability"}.issubset(kinds):
                errors.append(f"/components/{i}: verified freshness lacks source evidence")
            if component["compatibility"] != "verified" or component["availability"] != "available":
                errors.append(f"/components/{i}: verified freshness contradicts candidate state")
            if age is not None and any(age_origin - timestamp(e["checked_at"]) > timedelta(days=age) for e in component["evidence"]):
                errors.append(f"/components/{i}: evidence exceeds policy age")
        if not any(c["action"] != "defer" for c in report["components"]):
            errors.append("/freshness: verified freshness needs assessed components")

    for i, component in enumerate(report["components"]):
        if not safe_path(component["owner"]):
            errors.append(f"/components/{i}/owner: owner must be a project-relative file")
        if component["action"] != "defer" and component["selected"] is None:
            errors.append(f"/components/{i}/selected: assessed candidate needs a version")
        for j, evidence in enumerate(component["evidence"]):
            if timestamp(evidence["checked_at"]) > generated:
                errors.append(f"/components/{i}/evidence/{j}: evidence is later than report")
            if "artifact_id" in evidence and evidence["artifact_id"] not in artifact_ids:
                errors.append(f"/components/{i}/evidence/{j}: unknown artifact reference")
        if complete and component["action"] == "update" and report["policy"]["require_supported_updates"]:
            if component["support"] != "supported" or not any(e["kind"] == "support" for e in component["evidence"]):
                errors.append(f"/components/{i}: update lacks required support evidence")

    for i, check in enumerate(report["checks"]):
        if check["status"] != "passed" and not check["reason"]:
            errors.append(f"/checks/{i}/reason: non-passing check needs explanation")
        if not set(check["artifact_ids"]).issubset(artifact_ids):
            errors.append(f"/checks/{i}: unknown artifact reference")
        if check["status"] == "passed" and (not check["command"] or not check["artifact_ids"]):
            errors.append(f"/checks/{i}: passing check needs command and artifact evidence")
        if check["kind"] in {"unit-tests", "integration-tests"} and check["status"] == "passed":
            before, after = check.get("tests_before"), check.get("tests_after")
            if after is None or after == 0:
                errors.append(f"/checks/{i}: passing tests need nonzero executed count")
            if before is not None and after is not None and after < before and not check.get("tests_change_reason"):
                errors.append(f"/checks/{i}: reduced tests need accounted-for migration evidence")

    if complete:
        if report["mode"] == "upgrade-java" and not any(
            any(role in m.get("targets", {}) for role in ("compilation_target", "deployment_runtime"))
            for m in report["modules"]
        ):
            errors.append("/modules: complete Java upgrade needs an explicit requested API or runtime target")
        if report["freshness"] != "verified":
            errors.append("/freshness: complete implementation requires verified freshness")
        if any(c["required"] and c["status"] != "passed" for c in report["checks"]):
            errors.append("/checks: complete implementation has unmet required checks")
        if not any(c["kind"] == "build" and c["required"] and c["status"] == "passed" for c in report["checks"]):
            errors.append("/checks: complete implementation needs a required passing build")
        if not any(c["kind"] == "unit-tests" for c in report["checks"]):
            errors.append("/checks: complete implementation needs a unit-test outcome, including justified non-applicability")
        artifact_paths = {a["path"] for a in report["artifacts"]}
        if any(c["owner"] not in artifact_paths for c in report["components"] if c["action"] != "defer"):
            errors.append("/artifacts: complete implementation needs version-owner file hashes")
    if report["status"] != "complete" and not (report["limitations"] or report["next_actions"]):
        errors.append("/: incomplete report needs limitations or next actions")

    root = None
    if project_root is not None:
        root = Path(project_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Project root must be a directory")
    if require_complete and complete:
        snapshot = report.get("inputs_snapshot")
        if not snapshot or root is None:
            errors.append("/inputs_snapshot: completion needs a complete local input snapshot")
        else:
            captured = timestamp(snapshot["captured_at"])
            age = report["policy"]["evidence_max_age_days"]
            if captured > generated or (age is not None and validation_time - captured > timedelta(days=age)):
                errors.append("/inputs_snapshot: capture timestamp is future or stale")
            if any(not safe_path(path) for path in snapshot["files"]):
                errors.append("/inputs_snapshot: unsafe input path")
            try:
                exclusions = project_policy["input_scope"]["excluded_dirs"] if project_policy is not None else None
                current_files = capture(root, exclusions) if exclusions is not None else capture(root)
                if snapshot["files"] != current_files:
                    errors.append("/inputs_snapshot: current input set or hashes differ from validated inputs")
            except (OSError, ValueError):
                errors.append("/inputs_snapshot: cannot verify complete input coverage")
            graphs = snapshot["graphs"]
            if sorted(g["module"] for g in graphs) != sorted(module_paths):
                errors.append("/inputs_snapshot/graphs: resolved graph evidence needs every module exactly once")
            for graph in graphs:
                if not set(graph["artifact_ids"]).issubset(artifact_ids):
                    errors.append("/inputs_snapshot/graphs: unknown graph artifact reference")
                from execution import verify_execution
                execution_id = graph.get("execution_artifact_id")
                if not execution_id:
                    errors.append("/inputs_snapshot/graphs: graph needs collected execution evidence")
                else:
                    errors.extend(verify_execution(report, root, execution_id, kind="resolved-graph", policy_hash=policy_sha256, now=validation_time, module=graph["module"], graph_artifact_ids=graph["artifact_ids"]))
                    by_id = {a["id"]: a for a in report["artifacts"]}
                    if any(by_id.get(a, {}).get("kind") != "resolved-graph" for a in graph["artifact_ids"]):
                        errors.append("/inputs_snapshot/graphs: graph reference is not a resolved graph artifact")
            for check in report["checks"]:
                if check["status"] != "passed":
                    continue
                execution_id = check.get("execution_artifact_id")
                if not execution_id:
                    errors.append("/checks: passing check needs collected execution evidence")
                else:
                    errors.extend(verify_execution(report, root, execution_id, kind=check["kind"], policy_hash=policy_sha256, now=validation_time, check=check))
    for i, artifact in enumerate(report["artifacts"]):
        if not safe_path(artifact["path"]):
            errors.append(f"/artifacts/{i}/path: unsafe project-relative path")
            continue
        if root is None:
            continue
        path = root
        try:
            for part in PurePosixPath(artifact["path"]).parts:
                path = path / part
                if path.is_symlink():
                    raise ValueError("Symlink artifact")
            if not path.is_file():
                raise ValueError("Artifact is not a regular file")
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != artifact["sha256"]:
                errors.append(f"/artifacts/{i}: recorded hash does not match current artifact")
        except (OSError, ValueError):
            errors.append(f"/artifacts/{i}: artifact unavailable or unsafe")
    return sorted(set(errors))


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON property")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Non-standard JSON constant")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("--project-root", help="Verify artifact hashes against this directory")
    parser.add_argument("--require-complete", action="store_true", help="Gate on complete implementation; audits do not pass this gate")
    parser.add_argument("--policy", help="Independent, reviewed project policy required by the live completion gate")
    args = parser.parse_args()
    if args.require_complete and args.project_root is None:
        parser.error("--require-complete requires --project-root to check recorded artifacts")
    try:
        with Path(args.report).open("rb") as source:
            raw = source.read(MAX_REPORT_BYTES + 1)
        if len(raw) > MAX_REPORT_BYTES:
            raise ValueError("Report size limit")
        report = json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=reject_constant)
        project_policy, policy_hash = None, None
        if args.policy:
            from policy import load_policy
            project_policy, raw_policy = load_policy(args.policy)
            policy_hash = hashlib.sha256(raw_policy).hexdigest()
        errors = validate(report, args.project_root, require_complete=args.require_complete, project_policy=project_policy, policy_sha256=policy_hash)
    except (OSError, ValueError, UnicodeError, RuntimeError, RecursionError):
        print("Cannot validate report: check input, project root and pre-provisioned jsonschema 4.x", file=sys.stderr)
        return 2
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 2
    complete = report["status"] == "complete" and report["mode"] != "audit"
    print(json.dumps({"valid": True, "implementation_complete": complete, "artifact_hashes_checked": args.project_root is not None}))
    return 1 if args.require_complete and not complete else 0


if __name__ == "__main__":
    sys.exit(main())
