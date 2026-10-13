#!/usr/bin/env python3
"""Hash project inputs without executing builds. Fail closed on unreadable/symlink inputs."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path


# Deliberately small, visible default. Keep reports/logs under .java-modernize.
# Projects with source inputs here need a different explicit policy (see policy.py).
EXCLUDED_DIRS = frozenset({".git", ".gradle", "target", "build", ".java-modernize"})
MAX_FILES = 50000
MAX_BYTES = 2 * 1024 * 1024 * 1024


def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture(root, excluded_dirs=EXCLUDED_DIRS):
    root = Path(root).resolve(strict=True)
    files, total = {}, 0
    def failed(error):
        raise ValueError("Cannot enumerate all project inputs") from error
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=failed):
        dirs[:] = sorted(d for d in dirs if d not in excluded_dirs)
        base = Path(directory)
        if any((base / d).is_symlink() for d in dirs):
            raise ValueError("Input directory symlink requires explicit scope resolution")
        for name in sorted(names):
            path = base / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("Input is not a regular file")
            total += path.stat().st_size
            if total > MAX_BYTES or len(files) >= MAX_FILES:
                raise ValueError("Input snapshot exceeds bounded coverage")
            files[path.relative_to(root).as_posix()] = digest_file(path)
    if not files:
        raise ValueError("No project inputs captured")
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project")
    args = parser.parse_args()
    try:
        print(json.dumps({"captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "files": capture(args.project), "graphs": []}, indent=2))
    except (OSError, ValueError):
        parser.exit(2, "Cannot capture a complete input snapshot; inspect input scope and file access\n")


if __name__ == "__main__":
    main()
