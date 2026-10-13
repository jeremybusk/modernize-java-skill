#!/usr/bin/env python3
"""Create timestamped modernization runs and render/check Markdown from canonical JSON."""

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
from string import Template
import subprocess
import tempfile
from urllib.parse import quote, urlsplit

from snapshot import EXCLUDED_DIRS, capture, digest_file
from validate_report import MAX_REPORT_BYTES, no_duplicates, reject_constant, safe_path, timestamp, validate


ASSETS = Path(__file__).resolve().parents[1] / "assets"
PHASES = ("assessment", "plan", "execution", "validation", "completion")
RUN_ID = r"[0-9]{8}T[0-9]{12}Z-[a-z0-9]+(?:-[a-z0-9]+)*"


class RunError(ValueError):
    """A diagnostic with no interpolated private project values."""


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def read_json(path):
    with Path(path).open("rb") as source:
        raw = source.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise RunError("JSON exceeds size bound")
    return json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=reject_constant)


def local_path(root, relative):
    """Explicit root-relative paths only; reject symlinks even inside the root."""
    if not safe_path(relative):
        raise RunError("Unsafe relative path")
    path = Path(root)
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RunError("Symlink in local path")
    return path


def atomic_write(path, content):
    if path.is_symlink():
        raise RunError("Refusing to replace a symlink")
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as output:
            name = output.name
            output.write(content)
        os.replace(name, path)
    finally:
        if name and Path(name).exists():
            Path(name).unlink()


def write_json(path, data):
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def git_baseline(root):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, env=env, capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=normal", "--", "."], cwd=root, env=env, capture_output=True, text=True, timeout=10, check=True).stdout
        return {"revision": revision, "dirty": bool(status), "description": "Observed before creating this run; application-scoped status covers this directory."}
    except (OSError, subprocess.SubprocessError):
        return {"revision": None, "dirty": None, "description": "Git baseline unavailable; inspect the actual starting state."}


def acyclic(items, label):
    by_id = {item["id"]: item for item in items}
    if len(by_id) != len(items):
        raise RunError(label + " IDs must be unique")
    pending = {key: set(value["depends_on"]) for key, value in by_id.items()}
    if any(not dependencies <= by_id.keys() for dependencies in pending.values()):
        raise RunError(label + " dependency is unknown")
    while pending:
        ready = {key for key, dependencies in pending.items() if not dependencies}
        if not ready:
            raise RunError(label + " dependency cycle")
        pending = {key: dependencies - ready for key, dependencies in pending.items() if key not in ready}


def validate_manifest(data):
    from jsonschema import Draft202012Validator
    schema = read_json(ASSETS / "run.schema.json")
    Draft202012Validator.check_schema(schema)
    if list(Draft202012Validator(schema).iter_errors(data)):
        raise RunError("Run manifest violates schema")
    if timestamp(data["created_at"]) > timestamp(data["updated_at"]):
        raise RunError("Run update predates creation")
    if not data["run_id"].startswith(timestamp(data["created_at"]).strftime("%Y%m%dT%H%M%S%fZ") + "-"):
        raise RunError("Run ID differs from creation timestamp")
    acyclic(data["repositories"], "Repository")
    acyclic(data["batches"], "Batch")
    repos = {r["id"] for r in data["repositories"]}
    if len({f["id"] for f in data["findings"]}) != len(data["findings"]):
        raise RunError("Finding IDs must be unique")
    if any(f["repository"] not in repos for f in data["findings"]):
        raise RunError("Finding repository is unknown")
    if any(not set(b["repositories"]) <= repos for b in data["batches"]):
        raise RunError("Batch repository is unknown")
    for phase in data["phases"].values():
        if phase["status"] != "pending" and not phase["summary"].strip():
            raise RunError("Active or terminal phases require a summary")
    for name, phase in data["phases"].items():
        if phase["status"] == "not_applicable" and not (data["mode"] == "audit" and name in {"execution", "validation"}):
            raise RunError("Only audit execution/validation may be inapplicable")
        if phase["status"] == "complete":
            prior = PHASES[:PHASES.index(name)]
            if any(data["phases"][p]["status"] not in {"complete", "not_applicable"} for p in prior):
                raise RunError("A completed phase requires completed preceding phases")
    batches = {b["id"]: b for b in data["batches"]}
    for batch in batches.values():
        if batch["status"] == "not_applicable":
            raise RunError("Use a documented no-op batch instead of inapplicable execution")
        if batch["status"] in {"in_progress", "complete"} and any(batches[d]["status"] != "complete" for d in batch["depends_on"]):
            raise RunError("Batch dependencies must complete before execution")
        if batch["status"] == "complete" and not batch["result"].strip():
            raise RunError("Completed batch requires an actual result")
    if data["mode"] != "audit" and data["phases"]["plan"]["status"] == "complete" and not batches:
        raise RunError("Implementation plan requires testable batches, including a no-op if appropriate")
    if data["mode"] != "audit" and data["phases"]["execution"]["status"] == "complete":
        covered = {rid for b in batches.values() for rid in b["repositories"]}
        if covered != repos or any(b["status"] != "complete" for b in batches.values()):
            raise RunError("Execution is incomplete across the required repository scope")
    paths = []
    for repo in data["repositories"]:
        if not safe_path(repo["path"]):
            raise RunError("Unsafe repository path")
        path = Path(repo["path"])
        if any(path == old or path in old.parents or old in path.parents for old in paths):
            raise RunError("Repository scopes must not overlap; use modules within one report")
        paths.append(path)
        for field in ("report", "checkpoint"):
            if repo[field] and not safe_path(repo[field]["path"]):
                raise RunError("Unsafe report/checkpoint path")
    if data["scope_kind"] != "workspace" and len(paths) != 1:
        raise RunError("Multiple repositories require workspace scope")
    if any(not safe_url(item["url"]) for item in data.get("links", [])):
        raise RunError("Review links must be HTTP(S) URLs without credentials or whitespace")


def load_run(manifest):
    manifest = Path(manifest).absolute()
    # The fixed depth makes portable relative repository mappings unambiguous.
    directory = manifest.parent
    if directory.parent.name != "runs" or directory.parent.parent.name != ".java-modernize":
        raise RunError("Manifest must be in <scope>/.java-modernize/runs/<run-id>")
    root = directory.parent.parent.parent.resolve(strict=True)
    local_path(root, manifest.relative_to(root).as_posix())
    data = read_json(manifest)
    validate_manifest(data)
    if directory.name != data["run_id"] or manifest.name != data["run_id"] + "-run.json":
        raise RunError("Manifest filename/directory differs from run ID")
    for repo in data["repositories"]:
        if not local_path(root, repo["path"]).is_dir():
            raise RunError("Repository scope is unavailable")
    return data, root


def bound_reports(data, root):
    reports = {}
    for repo in data["repositories"]:
        binding = repo["report"]
        if binding is None:
            continue
        path = local_path(local_path(root, repo["path"]), binding["path"])
        if digest_file(path) != binding["sha256"]:
            raise RunError("Bound report changed; review and bind it again")
        report = read_json(path)
        if validate(report) or report["mode"] != data["mode"]:
            raise RunError("Bound report is invalid or uses a different mode")
        for key in ("revision", "dirty"):
            if repo["baseline"][key] is not None and repo["baseline"][key] != report["baseline"][key]:
                raise RunError("Report contradicts the recorded starting baseline")
        reports[repo["id"]] = report
    if data["phases"]["completion"]["status"] == "complete" or (data["mode"] != "audit" and data["phases"]["validation"]["status"] == "complete"):
        if len(reports) != len(data["repositories"]) or any(r["status"] != "complete" for r in reports.values()):
            raise RunError("Completion requires complete reports for every repository")
    return reports


def text(value):
    """Render all authored fields as text, never injected Markdown links/HTML."""
    value = "unknown" if value is None else str(value)
    value = html.escape(value, quote=False).replace("\r", " ").replace("\n", " ")
    value = re.sub(r"([\\`*_\[\]|])", r"\\\1", value)
    value = re.sub(r"^([#>+\-])", r"\\\1", value)
    return re.sub(r"^(\d+)([.)])(?=\s)", r"\1\\\2", value)


def table(headers, rows):
    rows = list(rows)
    if not rows:
        return "No observations recorded."
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"] + ["| " + " | ".join(text(cell) for cell in row) + " |" for row in rows])


def bullets(values):
    return "\n".join("- " + text(value) for value in values) or "None recorded; this does not establish absence."


def link(label, path, directory):
    relative = Path(os.path.relpath(path, directory)).as_posix()
    return "[" + text(label) + "](" + quote(relative, safe="/.-_") + ")"


def safe_url(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password and not any(c.isspace() or ord(c) < 32 for c in value)
    except ValueError:
        return False


def source_link(value, label=None):
    if safe_url(value):
        return "[" + text(label or value) + "](" + quote(value, safe=":/?&=%#@+;,-._~") + ")"
    return text(value)


def documents(data, root, directory, reports):
    run_id = data["run_id"]
    names = {p: run_id + "-" + ("completion-summary" if p == "completion" else p) + ".md" for p in PHASES}
    index_name = run_id + "-index.md"
    compact_name = run_id + "-report.md"
    metadata = lambda phase: "---\n" + "\n".join(k + ": " + json.dumps(v) for k, v in {
        "schema_version": 1, "run_id": run_id, "phase": phase, "updated_at": data["updated_at"],
        "manifest": run_id + "-run.json", "generated": True,
        "status": data["phases"][phase if phase in PHASES else "completion"]["status"],
    }.items()) + "\n---"
    navigation = [link("Canonical run JSON", directory / (run_id + "-run.json"), directory)]
    navigation += [link("Report" if data["layout"] == "compact" else p.title(), directory / (compact_name if data["layout"] == "compact" else names[p]), directory) for p in (("completion",) if data["layout"] == "compact" else PHASES)]
    common = {
        "metadata": metadata("index"), "title": text(data["title"]), "navigation": " · ".join(navigation),
        "outcome": text(data["phases"]["completion"]["summary"] or "Work has not been completed."),
        "next_action": "Next action: " + text(data["next_action"]),
        "scope": text(data["scope_kind"] + ": " + data["scope_reason"]),
        "repositories": table(["Repository", "Path from scope root", "Depends on"], ((r["id"], r["path"], ", ".join(r["depends_on"]) or "none") for r in data["repositories"])),
        "progress": table(["Phase", "Status", "Summary"], ((p, data["phases"][p]["status"], data["phases"][p]["summary"]) for p in PHASES)),
        "baselines": table(["Repository", "Starting revision", "Pre-existing changes", "Observation"], ((r["id"], r["baseline"]["revision"], r["baseline"]["dirty"], r["baseline"]["description"]) for r in data["repositories"])),
        "constraints": bullets(rid + ": " + value for rid, r in reports.items() for value in r["constraints"]),
        "findings": table(["ID", "Repository", "Priority", "Observation", "Action"], ((f["id"], f["repository"], f["priority"], f["observation"], f["action"]) for f in data["findings"])),
        "components": table(["Repository / component", "Owner", "Current → selected", "Decision", "Reason"], ((rid + "/" + c["id"], c["owner"], (str(c["current"]) if c["current"] is not None else "unknown") + " → " + (str(c["selected"]) if c["selected"] is not None else "unselected"), c["action"], c["reason"]) for rid, r in reports.items() for c in r["components"])),
        "batches": table(["Batch", "Repositories", "Dependencies", "Status", "Goal"], ((b["id"], ", ".join(b["repositories"]), ", ".join(b["depends_on"]) or "none", b["status"], b["goal"]) for b in data["batches"])),
        "criteria": table(["Batch", "Success criteria / checks", "Recovery boundary"], ((b["id"], b["validation"], b["recovery"]) for b in data["batches"])),
        "changes": table(["Batch", "Files (repository:path)", "Status", "Result / commit"], ((b["id"], ", ".join(b["files"]), b["status"], b["result"]) for b in data["batches"])),
        "checkpoints": table(["Repository", "Checkpoint path", "SHA-256"], ((r["id"], r["checkpoint"]["path"] if r["checkpoint"] else None, r["checkpoint"]["sha256"] if r["checkpoint"] else None) for r in data["repositories"])),
        "checks": table(["Repository / check", "Status", "Command", "Environment", "Tests before → after", "Reason"], ((rid + "/" + c["id"], c["status"], c["command"], c["environment"], str(c.get("tests_before", "unknown")) + " → " + str(c.get("tests_after", "unknown")), c.get("reason")) for rid, r in reports.items() for c in r["checks"])),
        "limitations": bullets([rid + ": " + value for rid, r in reports.items() for value in r["limitations"]] + [r["id"] + ": no evidence report is bound." for r in data["repositories"] if r["id"] not in reports]),
        "java_targets": table(["Repository / module", "Java role", "Before", "After", "Preserved"], ((rid + "/" + m["path"], role, m["before"][role], m["after"][role], role in m["preserve"]) for rid, r in reports.items() for m in r["modules"] for role in m["before"])),
        "check_summary": table(["Repository", "Report status", "Freshness", "Passed", "Failed", "Not run", "Not applicable"], ((rid, r["status"], r["freshness"], *(sum(c["status"] == status for c in r["checks"]) for status in ("passed", "failed", "not_run", "not_applicable"))) for rid, r in reports.items())),
        "next_actions": bullets([data["next_action"]] + [rid + ": " + value for rid, r in reports.items() for value in r["next_actions"]]),
        "recovery": bullets(b["id"] + ": " + b["recovery"] for b in data["batches"]),
        "deployment": text(data["deployment"]["status"] + ": " + data["deployment"]["details"]),
        "links": "\n".join("- " + source_link(item["url"], item["label"]) for item in data.get("links", [])) or "No commit, CI, review, or release links recorded.",
        "sources": "\n".join("- " + text(rid + "/" + c["id"] + " — " + e["kind"] + " — checked " + e["checked_at"]) + ": " + source_link(e["source"]) for rid, r in reports.items() for c in r["components"] for e in c["evidence"]) or "No dated source evidence recorded.",
    }
    evidence = []
    for repo in data["repositories"]:
        if repo["id"] not in reports:
            continue
        repo_root = local_path(root, repo["path"])
        evidence.append("- " + link(repo["id"] + " report", local_path(repo_root, repo["report"]["path"]), directory))
        for artifact in reports[repo["id"]]["artifacts"]:
            path = local_path(repo_root, artifact["path"])
            if not path.is_file():
                raise RunError("Artifact link is unavailable")
            evidence.append("- " + link(repo["id"] + "/" + artifact["id"], path, directory))
    common["evidence"] = "\n".join(evidence) or "No evidence report is bound."
    result = {index_name: Template((ASSETS / "run-templates/index.md").read_text(encoding="utf-8")).substitute(common)}
    sections = []
    for phase in PHASES:
        state = data["phases"][phase]
        values = dict(common, phase="Status: " + text(state["status"]) + "\n\n" + text(state["summary"] or "Not assessed yet.") + "\n\n" + bullets(state["notes"]))
        content = Template((ASSETS / ("run-templates/" + phase + ".md")).read_text(encoding="utf-8")).substitute(values)
        sections.append(content)
        if data["layout"] == "expanded":
            result[names[phase]] = metadata(phase) + "\n" + "\n".join(["", "# " + text(data["title"]) + " — " + phase.title(), "", link("Run index", directory / index_name, directory), "", content])
    if data["layout"] == "compact":
        result[compact_name] = metadata("report") + "\n\n# " + text(data["title"]) + "\n\n" + link("Run index", directory / index_name, directory) + "\n\n" + "\n".join(sections)
    return result


def render(manifest, *, check=False):
    data, root = load_run(manifest)
    reports = bound_reports(data, root)
    directory = Path(manifest).absolute().parent
    expected = documents(data, root, directory, reports)
    managed = {data["run_id"] + "-" + suffix + ".md" for suffix in (*PHASES[:-1], "completion-summary", "report", "index")}
    if any(local_path(directory, name).exists() for name in managed - expected.keys()):
        raise RunError("Conflicting generated layouts; restore the original layout or initialize a new run")
    for name, content in expected.items():
        path = local_path(directory, name)
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise RunError("Markdown is missing or differs from canonical JSON; render again")
        else:
            atomic_write(path, content)
    return data


def initialize(root, slug, repositories, *, title=None, mode="maintain-java", layout="expanded", scope_kind="repository", scope_reason="Explicit scope root selected for this modernization."):
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or len(slug) > 60:
        raise RunError("Choose an existing scope directory and a short lowercase slug")
    created = utc_now()
    run_id = timestamp(created).strftime("%Y%m%dT%H%M%S%fZ") + "-" + slug
    repos = []
    for repo_id, relative in repositories.items():
        project = local_path(root, relative)
        if not project.is_dir():
            raise RunError("Repository directory is unavailable")
        repos.append({"id": repo_id, "path": Path(relative).as_posix(), "depends_on": [], "baseline": git_baseline(project), "report": None, "checkpoint": None})
    data = {
        "schema_version": 1, "run_id": run_id, "created_at": created, "updated_at": created,
        "title": title or slug.replace("-", " ").title(), "mode": mode, "layout": layout,
        "scope_kind": scope_kind, "scope_reason": scope_reason, "repositories": repos,
        "phases": {p: {"status": "pending", "summary": "", "notes": []} for p in PHASES},
        "findings": [], "batches": [], "next_action": "Assess the baseline, constraints, version owners, and required checks.",
        "links": [],
        "deployment": {"status": "not_in_scope", "details": "No deployment has been performed by this run helper."},
    }
    validate_manifest(data)
    directory = local_path(root, ".java-modernize/runs/" + run_id)
    directory.mkdir(parents=True, exist_ok=False)
    manifest = directory / (run_id + "-run.json")
    write_json(manifest, data)
    render(manifest)
    # Convenience only: named runs remain authoritative. Never use a pointer for a gate.
    write_json(local_path(root, ".java-modernize/latest.json"), {"schema_version": 1, "run_id": run_id, "manifest": manifest.relative_to(root / ".java-modernize").as_posix()})
    return manifest


def assignments(values):
    result = {}
    for value in values:
        key, separator, path = value.partition("=")
        if not separator or not key or not path or key in result:
            raise RunError("Expected unique ID=path assignments")
        result[key] = path
    return result


def bind_report(manifest, repository, relative):
    data, root = load_run(manifest)
    repo = next((r for r in data["repositories"] if r["id"] == repository), None)
    if repo is None:
        raise RunError("Unknown repository ID")
    path = local_path(local_path(root, repo["path"]), relative)
    repo["report"] = {"path": relative, "sha256": digest_file(path)}
    bound_reports(data, root)
    data["updated_at"] = utc_now()
    write_json(Path(manifest), data)
    render(manifest)


def checkpoint(manifest, policies):
    from policy import load_policy
    data, root = load_run(manifest)
    if not policies.keys() <= {r["id"] for r in data["repositories"]}:
        raise RunError("Unknown checkpoint policy repository")
    pending = []
    for repo in data["repositories"]:
        project = local_path(root, repo["path"])
        excluded, policy_hash = sorted(EXCLUDED_DIRS), None
        if repo["id"] in policies:
            policy, raw = load_policy(policies[repo["id"]])
            excluded = policy["input_scope"]["excluded_dirs"]
            policy_hash = hashlib.sha256(raw).hexdigest()
        if ".java-modernize" not in excluded:
            raise RunError("Checkpoint policy must exclude generated run output")
        record = {"schema_version": 1, "captured_at": utc_now(), "revision": git_baseline(project)["revision"], "excluded_dirs": excluded, "policy_sha256": policy_hash, "files": capture(project, excluded)}
        name = timestamp(record["captured_at"]).strftime("%Y%m%dT%H%M%S%fZ") + "-checkpoint.json"
        path = local_path(project, ".java-modernize/runs/" + data["run_id"] + "/" + name)
        if path.exists():
            raise RunError("Checkpoint already exists")
        pending.append((repo, project, path, record))
    for repo, project, path, record in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive create preserves previous checkpoints even if invocations overlap.
        with path.open("x", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps(record, indent=2) + "\n")
        repo["checkpoint"] = {"path": path.relative_to(project).as_posix(), "sha256": digest_file(path)}
    data["updated_at"] = utc_now()
    write_json(Path(manifest), data)
    render(manifest)


def resume(manifest, policies):
    """Compare saved inputs; invalidate state without replaying edits or refreshing evidence."""
    from policy import load_policy
    data, root = load_run(manifest)
    if not policies.keys() <= {r["id"] for r in data["repositories"]}:
        raise RunError("Unknown resume policy repository")
    stale = set()
    for repo in data["repositories"]:
        project = local_path(root, repo["path"])
        try:
            binding = repo["checkpoint"]
            if binding is None:
                raise RunError("No checkpoint")
            path = local_path(project, binding["path"])
            if digest_file(path) != binding["sha256"]:
                raise RunError("Checkpoint hash changed")
            saved = read_json(path)
            excluded, policy_hash = sorted(EXCLUDED_DIRS), None
            if repo["id"] in policies:
                policy, raw = load_policy(policies[repo["id"]])
                excluded = policy["input_scope"]["excluded_dirs"]
                policy_hash = hashlib.sha256(raw).hexdigest()
            if saved["policy_sha256"] != policy_hash or set(saved["excluded_dirs"]) != set(excluded):
                raise RunError("Checkpoint scope or policy differs")
            if saved["files"] != capture(project, excluded) or saved["revision"] != git_baseline(project)["revision"]:
                raise RunError("Checkpoint inputs or revision differ")
            if repo["report"]:
                report_path = local_path(project, repo["report"]["path"])
                if digest_file(report_path) != repo["report"]["sha256"]:
                    raise RunError("Report drift")
        except (OSError, ValueError, KeyError, TypeError):
            stale.add(repo["id"])
    # Consumers of a changed repository need reconsideration too.
    while True:
        affected = stale | {r["id"] for r in data["repositories"] if stale.intersection(r["depends_on"])}
        if affected == stale:
            break
        stale = affected
    if stale:
        for phase in data["phases"].values():
            if phase["status"] != "pending":
                phase.update(status="stale", summary="Inputs, revision, policy, or evidence changed; reassess before continuing.")
        affected_batches = {b["id"] for b in data["batches"] if stale.intersection(b["repositories"])}
        while True:
            expanded = affected_batches | {b["id"] for b in data["batches"] if affected_batches.intersection(b["depends_on"])}
            if expanded == affected_batches:
                break
            affected_batches = expanded
        for batch in data["batches"]:
            if batch["id"] in affected_batches and batch["status"] != "pending":
                batch["status"] = "stale"
        data["next_action"] = "Reassess changed scope and recollect affected evidence: " + ", ".join(sorted(stale)) + ". Retained reports describe the previous state."
        data["updated_at"] = utc_now()
        write_json(Path(manifest), data)
        # Do not rebind changed reports automatically. Retain prior document/evidence bytes
        # until the author reviews the mismatch; the check command will reject drift.
        try:
            render(manifest)
        except (OSError, ValueError):
            pass
    return sorted(stale)


def check_completion(manifest, policies, *, now=None):
    """Aggregate existing independent live gates; no shell or report commands execute."""
    from policy import load_policy
    data = render(manifest, check=True)
    _, root = load_run(manifest)
    if data["mode"] == "audit" or any(p["status"] != "complete" for p in data["phases"].values()):
        raise RunError("Run is not a completed implementation")
    if set(policies) != {r["id"] for r in data["repositories"]}:
        raise RunError("Supply one independent policy per repository")
    reports = bound_reports(data, root)
    for repo in data["repositories"]:
        policy, raw = load_policy(policies[repo["id"]])
        errors = validate(reports[repo["id"]], local_path(root, repo["path"]), require_complete=True, now=now, project_policy=policy, policy_sha256=hashlib.sha256(raw).hexdigest())
        if errors:
            raise RunError("Repository live completion gate failed")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    init = commands.add_parser("init")
    init.add_argument("--scope-root", required=True)
    init.add_argument("--slug", required=True)
    init.add_argument("--repo", action="append", required=True, help="Stable ID=path relative to scope root; use app=. for a single project")
    init.add_argument("--title")
    init.add_argument("--mode", choices=["audit", "upgrade-java", "maintain-java", "modernize-code"], default="maintain-java")
    init.add_argument("--layout", choices=["compact", "expanded"], default="expanded")
    init.add_argument("--scope-kind", choices=["repository", "application", "workspace"], default="repository")
    init.add_argument("--scope-reason", default="Explicit scope root selected for this modernization.")
    for operation in ("render", "check", "checkpoint", "resume", "bind-report"):
        command = commands.add_parser(operation)
        command.add_argument("manifest")
        if operation in {"check", "checkpoint", "resume"}:
            command.add_argument("--policy", action="append", default=[], help="ID=independently reviewed policy file (relative to cwd or absolute)")
        if operation == "check":
            command.add_argument("--require-complete", action="store_true", help="Run independent live completion gates for every repository")
        if operation == "bind-report":
            command.add_argument("--repo", required=True)
            command.add_argument("--report", required=True, help="Path relative to that repository's root")
    args = parser.parse_args()
    try:
        if args.operation == "init":
            manifest = initialize(args.scope_root, args.slug, assignments(args.repo), title=args.title, mode=args.mode, layout=args.layout, scope_kind=args.scope_kind, scope_reason=args.scope_reason)
            print(json.dumps({"manifest": str(manifest)}))
        elif args.operation == "bind-report":
            bind_report(args.manifest, args.repo, args.report)
            print('{"bound": true}')
        elif args.operation == "checkpoint":
            checkpoint(args.manifest, assignments(args.policy))
            print('{"checkpoint_saved": true}')
        elif args.operation == "resume":
            stale = resume(args.manifest, assignments(args.policy))
            print(json.dumps({"stale_repositories": stale, "live_completion_checked": False}))
            return 1 if stale else 0
        elif args.operation == "check" and args.require_complete:
            data = check_completion(args.manifest, assignments(args.policy))
            print(json.dumps({"valid": True, "run_id": data["run_id"], "live_completion_checked": True, "implementation_complete": True}))
        else:
            if args.operation == "check" and args.policy:
                raise RunError("Use --require-complete to check independent policies")
            data = render(args.manifest, check=args.operation == "check")
            print(json.dumps({"valid": True, "run_id": data["run_id"], "live_completion_checked": False}))
    except RunError as error:
        parser.exit(2, str(error) + "\n")
    except (OSError, ValueError, RuntimeError, ImportError, UnicodeError, RecursionError) as error:
        # Error details deliberately omit project values, which can contain secrets.
        parser.exit(2, "Run operation failed: " + type(error).__name__ + "; inspect schema, paths, bindings, and generated document consistency\n")


if __name__ == "__main__":
    raise SystemExit(main())
