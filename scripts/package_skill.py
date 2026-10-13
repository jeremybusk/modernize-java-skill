#!/usr/bin/env python3
"""Build a stable skill archive with an internal file manifest and external SHA-256."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "java-modernize"
MANIFEST = "PACKAGE-MANIFEST.json"


def package(output, package_root=PACKAGE):
    package_root = Path(package_root)
    members = {}
    for path in sorted(package_root.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError("Skill package may not contain symlinks")
        if path.is_file():
            relative = path.relative_to(package_root).as_posix()
            if relative == MANIFEST:
                raise ValueError("Package manifest is generated, not an input file")
            members[relative] = path.read_bytes()
    for required in ("SKILL.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
        if required not in members:
            raise ValueError("Skill package is missing required instructions or licensing")
    manifest = {"format_version": 1, "skill": package_root.name, "files": {name: hashlib.sha256(content).hexdigest() for name, content in members.items()}}
    members[MANIFEST] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output = Path(output)
    # Do not put the generated archive or checksum back inside its own inputs.
    if output.resolve().is_relative_to(package_root.resolve()):
        raise ValueError("Output must be outside the skill directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, content in sorted(members.items()):
            info = ZipInfo(package_root.name + "/" + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_DEFLATED
            bundle.writestr(info, content, compress_type=ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(digest + "  " + output.name + "\n", encoding="utf-8")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/java-modernize.zip")
    args = parser.parse_args()
    try:
        digest = package(args.output)
    except (OSError, ValueError):
        parser.error("Cannot package skill: check source files and output location")
    print(digest + "  " + args.output.name)


if __name__ == "__main__":
    main()
