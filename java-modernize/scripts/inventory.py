#!/usr/bin/env python3
"""Read-only configuration inventory. Never execute a build or infer effective versions."""

import argparse
from fnmatch import fnmatchcase
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
    "repository-or-trust": re.compile(
        r"<mirrors>|<mirror>|<repositories>|<pluginRepositories>|<servers>|"
        r"pluginManagement|buildscript|dependencyResolutionManagement|"
        r"exclusiveContent|includeGroup|repositoriesMode|verification-metadata|"
        r"distributionSha256Sum"
    ),
}


def category(relative):
    """Recognize likely configuration, including custom Gradle catalogs/plugins."""
    name = relative.name
    parts = relative.parts
    if name in {"mvnw", "mvnw.cmd", "gradlew", "gradlew.bat"}:
        return "wrapper-launcher"
    if name.endswith((".kt", ".java", ".groovy")) and any(p in {"buildSrc", "build-logic"} for p in parts):
        return "build-convention-source"
    if name in {"jvm.config", "jvm.options"}:
        return "runtime-config"
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


def inventory(root, max_file_bytes=1024 * 1024, excludes=(), include_configs=(), max_configs=10000):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Project root must be a directory")
    if max_file_bytes < 1 or max_configs < 1:
        raise ValueError("Inventory limits must be positive")
    files, skipped, excluded_dirs = [], [], []
    seen = set()
    considered, excluded_files, truncated = 0, 0, False

    def excluded(relative):
        return any(fnmatchcase(relative.as_posix(), pattern) for pattern in excludes)

    def inspect(path, relative, kind):
        nonlocal considered, excluded_files, truncated
        name = relative.as_posix()
        if name in seen:
            return
        seen.add(name)
        if excluded(relative):
            excluded_files += 1
            return
        if considered >= max_configs:
            truncated = True
            return
        considered += 1
        try:
            # Reject symlink ancestors, including explicitly included configs.
            current = root
            for part in relative.parts:
                current /= part
                if current.is_symlink():
                    skipped.append({"path": name, "reason": "symlink"})
                    return
            if not path.is_file():
                skipped.append({"path": name, "reason": "not-regular-file"})
                return
            with path.open("rb") as source:
                raw = source.read(max_file_bytes + 1)
            if len(raw) > max_file_bytes:
                skipped.append({"path": name, "reason": "size-limit"})
                return
            content = raw.decode("utf-8-sig")
        except (OSError, UnicodeError):
            skipped.append({"path": name, "reason": "unreadable-or-non-utf8"})
            return
        matches = [
            {"line": number, "signal": signal}
            for number, line in enumerate(content.splitlines(), 1)
            for signal, pattern in SIGNALS.items()
            if pattern.search(line)
        ]
        files.append({"path": name, "category": kind, "evidence": matches})

    def walk_error(error):
        # Report only a path, never arbitrary file content or OS error messages.
        path = Path(error.filename) if error.filename else root
        skipped.append({"path": str(path.relative_to(root)), "reason": "unreadable-directory"})

    for value in include_configs:
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts or "\\" in value or ":" in value:
            raise ValueError("Explicit configs must be project-relative")
        inspect(root / relative, relative, category(relative) or "explicit-config")

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        keep = []
        for name in sorted(dirs):
            path = Path(directory, name)
            relative = path.relative_to(root)
            reason = "symlink-directory" if path.is_symlink() else "default-exclusion" if name in IGNORE_DIRS else "requested-exclusion" if excluded(relative) else None
            if reason:
                excluded_dirs.append({"path": relative.as_posix(), "reason": reason})
            else:
                keep.append(name)
        dirs[:] = keep
        for name in sorted(names):
            path = Path(directory, name)
            relative = path.relative_to(root)
            kind = category(relative)
            if kind is None:
                continue
            inspect(path, relative, kind)
            if truncated:
                break
        if truncated:
            break
    return {
        "schema_version": 1,
        "scope": "static-configuration-inventory",
        "effective_versions_resolved": False,
        "discovery_truncated": truncated,
        "excluded_directories": sorted(excluded_dirs, key=lambda item: item["path"]),
        "excluded_file_count": excluded_files,
        "limitations": [
            "Signals can match comments and cannot evaluate build logic or inheritance.",
            "Generated/cache directories and symlink directories are not traversed.",
            "Only recognized configuration names are inventoried; inspect other project files as needed.",
            "Explicit includes scan only named files; exclusions and resource limits can leave coverage incomplete.",
            "No build execution, network lookup, writes, or effective version selection occurs.",
        ],
        "files": sorted(files, key=lambda item: item["path"]),
        "skipped": sorted(skipped, key=lambda item: item["path"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--max-file-bytes", type=int, default=1024 * 1024)
    parser.add_argument("--max-configs", type=int, default=10000)
    parser.add_argument("--exclude", action="append", default=[], help="Exclude a project-relative POSIX glob; repeat as needed")
    parser.add_argument("--include-config", action="append", default=[], help="Also inspect a named project-relative config file")
    args = parser.parse_args()
    if args.max_file_bytes < 1 or args.max_configs < 1:
        parser.error("Inventory limits must be positive")
    try:
        result = inventory(args.project_root, args.max_file_bytes, args.exclude, args.include_config, args.max_configs)
    except (OSError, ValueError):
        print("Cannot inventory project: check the root, config paths and resource limits", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
