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
from urllib.parse import quote

from snapshot import digest_file
from validate_report import MAX_REPORT_BYTES, no_duplicates, reject_constant, safe_path, timestamp, validate


ASSETS = Path(__file__).resolve().parents[1] / "assets"
PHASES = ("assessment", "plan", "execution", "validation", "completion")
RUN_ID = r"[0-9]{8}T[0-9]{12}Z-[a-z0-9]+(?:-[a-z0-9]+)*"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def read_json(path):
    with Path(path).open("rb") as source:
        raw = source.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("JSON exceeds size bound")
    return json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=reject_constant)


def local_path(root, relative):
    """Explicit root-relative paths only; reject symlinks even inside the root."""
    if not safe_path(relative):
        raise ValueError("Unsafe relative path")
    path = Path(root)
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("Symlink in local path")
    return path


def atomic_write(path, content):
    if path.is_symlink():
        raise ValueError("Refusing to replace a symlink")
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
        raise ValueError(label + " IDs must be unique")
    pending = {key: set(value["depends_on"]) for key, value in by_id.items()}
    if any(not dependencies <= by_id.keys() for dependencies in pending.values()):
        raise ValueError(label + " dependency is unknown")
    while pending:
        ready = {key for key, dependencies in pending.items() if not dependencies}
        if not ready:
            raise ValueError(label + " dependency cycle")
        pending = {key: dependencies - ready for key, dependencies in pending.items() if key not in ready}


def validate_manifest(data):
    from jsonschema import Draft202012Validator
    schema = read_json(ASSETS / "run.schema.json")
    Draft202012Validator.check_schema(schema)
    if list(Draft202012Validator(schema).iter_errors(data)):
        raise ValueError("Run manifest violates schema")
    if timestamp(data["created_at"]) > timestamp(data["updated_at"]):
        raise ValueError("Run update predates creation")
    if not data["run_id"].startswith(timestamp(data["created_at"]).strftime("%Y%m%dT%H%M%S%fZ") + "-"):
        raise ValueError("Run ID differs from creation timestamp")
    acyclic(data["repositories"], "Repository")
    acyclic(data["batches"], "Batch")
    repos = {r["id"] for r in data["repositories"]}
    if len({f["id"] for f in data["findings"]}) != len(data["findings"]):
        raise ValueError("Finding IDs must be unique")
    if any(f["repository"] not in repos for f in data["findings"]):
        raise ValueError("Finding repository is unknown")
    if any(not set(b["repositories"]) <= repos for b in data["batches"]):
        raise ValueError("Batch repository is unknown")
    for phase in data["phases"].values():
        if phase["status"] != "pending" and not phase["summary"].strip():
            raise ValueError("Active or terminal phases require a summary")
    for name, phase in data["phases"].items():
        if phase["status"] == "not_applicable" and not (data["mode"] == "audit" and name in {"execution", "validation"}):
            raise ValueError("Only audit execution/validation may be inapplicable")
    paths = []
    for repo in data["repositories"]:
        if not safe_path(repo["path"]):
            raise ValueError("Unsafe repository path")
        path = Path(repo["path"])
        if any(path == old or path in old.parents or old in path.parents for old in paths):
            raise ValueError("Repository scopes must not overlap; use modules within one report")
        paths.append(path)
        for field in ("report", "checkpoint"):
            if repo[field] and not safe_path(repo[field]["path"]):
                raise ValueError("Unsafe report/checkpoint path")
    if data["scope_kind"] != "workspace" and len(paths) != 1:
        raise ValueError("Multiple repositories require workspace scope")


def load_run(manifest):
    manifest = Path(manifest).absolute()
    # The fixed depth makes portable relative repository mappings unambiguous.
    directory = manifest.parent
    if directory.parent.name != "runs" or directory.parent.parent.name != ".java-modernize":
        raise ValueError("Manifest must be in <scope>/.java-modernize/runs/<run-id>")
    root = directory.parent.parent.parent.resolve(strict=True)
    local_path(root, manifest.relative_to(root).as_posix())
    data = read_json(manifest)
    validate_manifest(data)
    if directory.name != data["run_id"] or manifest.name != data["run_id"] + "-run.json":
        raise ValueError("Manifest filename/directory differs from run ID")
    for repo in data["repositories"]:
        if not local_path(root, repo["path"]).is_dir():
            raise ValueError("Repository scope is unavailable")
    return data, root


def bound_reports(data, root):
    reports = {}
    for repo in data["repositories"]:
        binding = repo["report"]
        if binding is None:
            continue
        path = local_path(local_path(root, repo["path"]), binding["path"])
        if digest_file(path) != binding["sha256"]:
            raise ValueError("Bound report changed; review and bind it again")
        report = read_json(path)
        if validate(report) or report["mode"] != data["mode"]:
            raise ValueError("Bound report is invalid or uses a different mode")
        reports[repo["id"]] = report
    return reports


def text(value):
    """Render all authored fields as text, never injected Markdown links/HTML."""
    value = "unknown" if value is None else str(value)
    value = html.escape(value, quote=False).replace("\r", " ").replace("\n", " ")
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value)


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


def documents(data, root, directory, reports):
    run_id = data["run_id"]
    names = {p: run_id + "-" + ("completion-summary" if p == "completion" else p) + ".md" for p in PHASES}
    index_name = run_id + "-index.md"
    compact_name = run_id + "-report.md"
    metadata = lambda phase: "---\n" + "\n".join(k + ": " + json.dumps(v) for k, v in {
        "schema_version": 1, "run_id": run_id, "phase": phase, "updated_at": data["updated_at"],
        "manifest": run_id + "-run.json", "generated": True,
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
        "components": table(["Repository / component", "Owner", "Current → selected", "Decision", "Reason"], ((rid + "/" + c["id"], c["owner"], str(c["current"]) + " → " + str(c["selected"]), c["action"], c["reason"]) for rid, r in reports.items() for c in r["components"])),
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
                raise ValueError("Artifact link is unavailable")
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
            result[names[phase]] = metadata(phase) + "\n" + "\n".join(["", link("Run index", directory / index_name, directory), "", content])
    if data["layout"] == "compact":
        result[compact_name] = metadata("report") + "\n\n" + link("Run index", directory / index_name, directory) + "\n\n" + "\n".join(sections)
    return result


def render(manifest, *, check=False):
    data, root = load_run(manifest)
    reports = bound_reports(data, root)
    directory = Path(manifest).absolute().parent
    expected = documents(data, root, directory, reports)
    for name, content in expected.items():
        path = local_path(directory, name)
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise ValueError("Markdown is missing or differs from canonical JSON; render again")
        else:
            atomic_write(path, content)
    return data


def initialize(root, slug, repositories, *, title=None, mode="maintain-java", layout="expanded", scope_kind="repository", scope_reason="Explicit scope root selected for this modernization."):
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or len(slug) > 60:
        raise ValueError("Choose an existing scope directory and a short lowercase slug")
    created = utc_now()
    run_id = timestamp(created).strftime("%Y%m%dT%H%M%S%fZ") + "-" + slug
    repos = []
    for repo_id, relative in repositories.items():
        project = local_path(root, relative)
        if not project.is_dir():
            raise ValueError("Repository directory is unavailable")
        repos.append({"id": repo_id, "path": Path(relative).as_posix(), "depends_on": [], "baseline": git_baseline(project), "report": None, "checkpoint": None})
    data = {
        "schema_version": 1, "run_id": run_id, "created_at": created, "updated_at": created,
        "title": title or slug.replace("-", " ").title(), "mode": mode, "layout": layout,
        "scope_kind": scope_kind, "scope_reason": scope_reason, "repositories": repos,
        "phases": {p: {"status": "pending", "summary": "", "notes": []} for p in PHASES},
        "findings": [], "batches": [], "next_action": "Assess the baseline, constraints, version owners, and required checks.",
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
            raise ValueError("Expected unique ID=path assignments")
        result[key] = path
    return result


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
    for operation in ("render", "check"):
        command = commands.add_parser(operation)
        command.add_argument("manifest")
    args = parser.parse_args()
    try:
        if args.operation == "init":
            manifest = initialize(args.scope_root, args.slug, assignments(args.repo), title=args.title, mode=args.mode, layout=args.layout, scope_kind=args.scope_kind, scope_reason=args.scope_reason)
            print(json.dumps({"manifest": str(manifest)}))
        else:
            data = render(args.manifest, check=args.operation == "check")
            print(json.dumps({"valid": True, "run_id": data["run_id"], "live_completion_checked": False}))
    except (OSError, ValueError, RuntimeError, ImportError, UnicodeError, RecursionError) as error:
        # Error details deliberately omit project values, which can contain secrets.
        parser.exit(2, "Run operation failed: " + type(error).__name__ + "; inspect schema, paths, bindings, and generated document consistency\n")


if __name__ == "__main__":
    main()
