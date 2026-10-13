#!/usr/bin/env python3
"""Validate an independent, reviewable project policy; never infer organizational rules."""

import argparse
import json
from pathlib import Path, PurePosixPath


SCHEMA = Path(__file__).resolve().parents[1] / "assets/project-policy.schema.json"


def validate_policy(policy):
    from jsonschema import Draft202012Validator
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = ["/policy: schema violation (" + e.validator + ")" for e in Draft202012Validator(schema).iter_errors(policy)]
    if errors:
        return sorted(set(errors))
    for collection, key in (("modules", "path"), ("components", "id"), ("checks", "id")):
        values = [entry[key] for entry in policy[collection]]
        if len(values) != len(set(values)):
            errors.append("/policy/" + collection + ": duplicate scope")
    for value in [m["path"] for m in policy["modules"]] + [c["owner"] for c in policy["components"]]:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or any(c in value for c in ("\\", ":", "\x00")):
            errors.append("/policy: unsafe scope path")
    for name in policy["input_scope"]["excluded_dirs"]:
        if name in {".", ".."} or any(c in name for c in ("/", "\\", ":", "\x00")):
            errors.append("/policy/input_scope: exclusions must be directory names")
    for kind in ("build", "unit-tests"):
        if not any(c["kind"] == kind for c in policy["checks"]):
            errors.append("/policy/checks: build and unit-test outcomes must be specified")
    if any(c["kind"] == "build" and c["allowed_statuses"] != ["passed"] for c in policy["checks"]):
        errors.append("/policy/checks: a build must pass")
    for c in policy["components"]:
        if not c["selected_versions"] and any(a != "defer" for a in c["allowed_actions"]):
            errors.append("/policy/components: assessed components need permitted exact versions")
    for m in policy["modules"]:
        if policy["mode"] == "upgrade-java" and not m["targets"]:
            errors.append("/policy/modules: upgrades need selected Java targets")
    return sorted(set(errors))


def load_policy(path):
    from validate_report import no_duplicates, reject_constant, MAX_REPORT_BYTES
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Policy must be a regular file")
    with path.open("rb") as source:
        raw = source.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("Policy size limit")
    policy = json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=reject_constant)
    errors = validate_policy(policy)
    if errors:
        raise ValueError("Invalid project policy")
    return policy, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy")
    args = parser.parse_args()
    try:
        load_policy(args.policy)
    except (OSError, ValueError, UnicodeError, RecursionError, ImportError):
        parser.exit(2, "Cannot validate project policy; check schema, scope and prerequisites\n")
    print('{"valid": true}')


if __name__ == "__main__":
    main()
