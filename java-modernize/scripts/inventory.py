#!/usr/bin/env python3
"""Read-only configuration inventory. Never execute a build or infer effective versions."""

import argparse
import json
import os
from pathlib import Path
import re
import sys


IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".gradle", ".m2", ".idea", ".venv", "venv",
    "node_modules", "target", "build", "out", "dist", "__pycache__",
}
SIGNALS = {
    "java-release-or-language": re.compile(
        r"maven\.compiler\.(?:release|source|target)|<java\.version>|"
        r"<(?:release|source|target)>|options\.release|sourceCompatibility|"
        r"targetCompatibility|jvmTarget|--release\b"
    ),
    "compiler-or-test-toolchain": re.compile(
        r"toolchain|JavaLanguageVersion|languageVersion|javaCompiler|javaLauncher|"
        r"jvmToolchain|jdkHome|<jdk>|<jdkToolchain>"
    ),
    "runtime-or-ci-java": re.compile(
        r"java-version|jdk-version|JAVA_HOME|JAVA_TOOL_OPTIONS|JDK_JAVA_OPTIONS|"
        r"^\s*java\s*[=:]|requireJavaVersion|org\.gradle\.java\.home|"
        r"toolchainVersion|^\s*jdk\s*[=:]"
    ),
    "parent-platform-or-catalog": re.compile(
        r"<parent>|<dependencyManagement>|<scope>import</scope>|\bplatform\s*\(|"
        r"enforcedPlatform|versionCatalogs|version\.ref|\[versions\]|\bbom\b",
        re.IGNORECASE,
    ),
    "dependency-or-plugin": re.compile(
        r"<dependency>|<plugin>|<extension>|<version>|\bplugins\b|"
        r"\b(?:implementation|api|runtimeOnly|testImplementation|annotationProcessor|"
        r"kapt|ksp)\b|\[libraries\]|\[plugins\]"
    ),
    "wrapper-or-image": re.compile(
        r"distributionUrl|distributionSha256Sum|wrapperUrl|^\s*FROM\s+|"
        r"\bimage\s*:|\buses\s*:|builder\s*="
    ),
    "preview-agent-or-access": re.compile(
        r"--enable-preview|--add-opens|--add-exports|--enable-native-access|"
        r"-javaagent:|-agentlib:|-XX:|annotationProcessorPaths|<proc>"
    ),
}


def category(relative):
    """Recognize likely configuration, including custom Gradle catalogs/plugins."""
    name = relative.name
    parts = relative.parts
    if name == "pom.xml" or name in {"toolchains.xml", "settings.xml"}:
        return "maven"
    if ".mvn" in parts:
        return "maven-wrapper-or-config"
    if name.endswith((".gradle", ".gradle.kts")) or name == "gradle.properties":
        return "gradle"
    if "gradle" in parts and name in {"gradle-wrapper.properties", "gradle-daemon-jvm.properties"}:
        return "gradle-wrapper-or-config"
    if name in {".sdkmanrc", ".tool-versions", ".java-version", "mise.toml", ".mise.toml"}:
        return "version-manager"
    if name.endswith(".toml"):
        return "catalog-or-tool-config"
    if name.lower().startswith("dockerfile") or name.endswith(".dockerfile"):
        return "container"
    if name in {"Jenkinsfile", ".gitlab-ci.yml", "azure-pipelines.yml", "buildspec.yml"}:
        return "ci"
    if name.endswith((".yml", ".yaml")):
        if (".github" in parts and "workflows" in parts) or ".circleci" in parts:
            return "ci"
        return "deployment-or-app-config"
    if name in {"renovate.json", "renovate.json5", ".renovaterc", ".renovaterc.json"}:
        return "update-automation"
    if name.endswith(".lockfile") or name == "gradle.lockfile":
        return "dependency-lock"
    if name == "verification-metadata.xml":
        return "dependency-verification"
    return None


def inventory(root, max_file_bytes=1024 * 1024):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Project root must be a directory")
    files, skipped = [], []

    def walk_error(error):
        # Report only a path, never arbitrary file content or OS error messages.
        path = Path(error.filename) if error.filename else root
        skipped.append({"path": str(path.relative_to(root)), "reason": "unreadable-directory"})

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS and not Path(directory, d).is_symlink())
        for name in sorted(names):
            path = Path(directory, name)
            relative = path.relative_to(root)
            kind = category(relative)
            if kind is None:
                continue
            if path.is_symlink():
                skipped.append({"path": relative.as_posix(), "reason": "symlink"})
                continue
            try:
                if not path.is_file():
                    skipped.append({"path": relative.as_posix(), "reason": "not-regular-file"})
                    continue
                # Bound reads even if a file grows after discovery.
                with path.open("rb") as source:
                    raw = source.read(max_file_bytes + 1)
                if len(raw) > max_file_bytes:
                    skipped.append({"path": relative.as_posix(), "reason": "size-limit"})
                    continue
                content = raw.decode("utf-8-sig")
            except (OSError, UnicodeError):
                skipped.append({"path": relative.as_posix(), "reason": "unreadable-or-non-utf8"})
                continue
            matches = [
                {"line": number, "signal": signal}
                for number, line in enumerate(content.splitlines(), 1)
                for signal, pattern in SIGNALS.items()
                if pattern.search(line)
            ]
            # No raw lines, values, credentials, environment, or dependency coordinates.
            files.append({"path": relative.as_posix(), "category": kind, "evidence": matches})
    return {
        "schema_version": 1,
        "scope": "static-configuration-inventory",
        "effective_versions_resolved": False,
        "limitations": [
            "Signals can match comments and cannot evaluate build logic or inheritance.",
            "Generated/cache directories and symlink directories are not traversed.",
            "Only recognized configuration names are inventoried; inspect other project files as needed.",
            "No build execution, network lookup, writes, or effective version selection occurs.",
        ],
        "files": sorted(files, key=lambda item: item["path"]),
        "skipped": sorted(skipped, key=lambda item: item["path"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--max-file-bytes", type=int, default=1024 * 1024)
    args = parser.parse_args()
    if args.max_file_bytes < 1:
        parser.error("--max-file-bytes must be positive")
    try:
        result = inventory(args.project_root, args.max_file_bytes)
    except (OSError, ValueError):
        print("Cannot read the project root as a directory", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
