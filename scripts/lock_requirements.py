#!/usr/bin/env python3
"""Write a wheel-only hash lock from an explicit pip resolution and official PyPI metadata."""

import argparse
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resolution", type=Path, help="pip --report JSON resolved for the oldest supported Python")
    parser.add_argument("--output", type=Path, default=ROOT / "requirements-dev.txt")
    args = parser.parse_args()
    resolution = json.loads(args.resolution.read_text(encoding="utf-8"))
    versions = {}
    for package in resolution["install"]:
        name = re.sub(r"[-_.]+", "-", package["metadata"]["name"]).lower()
        version = package["metadata"]["version"]
        if not re.fullmatch(r"[a-z0-9-]+", name) or not re.fullmatch(r"[0-9][a-zA-Z0-9.!+_-]*", version):
            raise ValueError("Unsupported package name/version")
        versions[name] = version
    for line in (ROOT / "requirements-dev.in").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==")
        if versions.get(re.sub(r"[-_.]+", "-", name).lower()) != version:
            raise ValueError("Resolution does not preserve direct requirements")
    lines = ["# Complete development/CI lock; Python 3.10+; wheels only.",
             "# Regenerate from requirements-dev.in using scripts/lock_requirements.py.",
             "# Hashes: official https://pypi.org/pypi/<package>/<version>/json metadata.",
             "--require-hashes", "--only-binary=:all:", ""]
    for name, version in sorted(versions.items()):
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=30) as response:
            metadata = json.load(response)
        hashes = sorted({item["digests"]["sha256"] for item in metadata["urls"] if item["packagetype"] == "bdist_wheel" and not item.get("yanked")})
        if not hashes or any(not re.fullmatch(r"[a-f0-9]{64}", digest) for digest in hashes):
            raise ValueError("No valid non-yanked wheel hashes")
        lines.append(name + "==" + version + " \\")
        lines.extend("    --hash=sha256:" + digest + (" \\" if i < len(hashes) - 1 else "") for i, digest in enumerate(hashes))
        lines.append("")
        print(name + "==" + version + ": " + str(len(hashes)) + " wheel hashes", flush=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
