#!/usr/bin/env python3
"""Download a pinned Linux x64 test JDK into a temporary tool directory."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request
import zipfile


# Historical integration tuple, not the skill's recommendation of a latest JDK.
LOCKS = {
    "25": ("25.0.4+7", "https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4%2B7/OpenJDK25U-jdk_x64_linux_hotspot_25.0.4_7.tar.gz", "e58fcdcd637b25c03ca84cbbcefc70d11efb8f4b4cbd05decc9f661769d77f94"),
    "8": ("8u504-b01", "https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u504-b01/OpenJDK8U-jdk_x64_linux_hotspot_8u504b01.tar.gz", "9c70e102f527ac674ac2fe9c7d47b9a04e2d19842ba5ab8e9b33f368bbadfaea"),
}
GRADLE_VERSION = "8.14.3"
GRADLE_SHA256 = "bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531"
MAVEN_VERSION = "3.9.12"
MAVEN_SHA512 = "0a1be79f02466533fc1a80abbef8796e4f737c46c6574ede5658b110899942a94db634477dfd3745501c80aef9aac0d4f841d38574373f7e2d24cce89d694f70"


def bootstrap(directory, feature="25"):
    version, url, expected = LOCKS[feature]
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / ("temurin-" + version + ".tar.gz")
    if not archive.exists():
        temporary = archive.with_suffix(".download")
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 600 * 1024 * 1024:
                    raise ValueError("JDK download exceeds size limit")
                output.write(chunk)
        temporary.replace(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError("Downloaded JDK does not match pinned vendor checksum")
    with tarfile.open(archive) as bundle:
        names = bundle.getnames()
        roots = {PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts}
        if len(roots) != 1 or any(name.startswith("/") or ".." in PurePosixPath(name).parts for name in names):
            raise ValueError("Unexpected JDK archive root")
        home = directory / roots.pop()
        if not (home / "bin/javac").is_file():
            # Current Python 3.10+ security releases provide the data filter.
            if not hasattr(tarfile, "data_filter"):
                raise RuntimeError("Use a Python security release providing tarfile.data_filter")
            bundle.extractall(directory, filter="data")
    result = {"jdk_home": str(home.resolve()), "version": version, "source": url, "sha256": expected}
    (directory / ("jdk" + feature + ".json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default="/tmp/java-modernize-tools")
    parser.add_argument("--jdk-feature", choices=sorted(LOCKS), default="25")
    parser.add_argument("--gradle", action="store_true", help="Download the pinned Gradle integration distribution instead")
    parser.add_argument("--maven", action="store_true", help="Download the pinned Maven integration distribution instead")
    args = parser.parse_args()
    if args.gradle and args.maven:
        parser.error("Select only one build-tool distribution")
    result = bootstrap_maven(args.directory) if args.maven else bootstrap_gradle(args.directory) if args.gradle else bootstrap(args.directory, args.jdk_feature)
    print(json.dumps(result, indent=2))


def bootstrap_gradle(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    name = "gradle-" + GRADLE_VERSION
    url = "https://services.gradle.org/distributions/" + name + "-bin.zip"
    archive = directory / (name + "-bin.zip")
    if not archive.exists():
        temporary = archive.with_suffix(".download")
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 300 * 1024 * 1024:
                    raise ValueError("Gradle download exceeds size limit")
                output.write(chunk)
        temporary.replace(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != GRADLE_SHA256:
        raise ValueError("Gradle distribution does not match the pinned vendor checksum")
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != name or "\\" in item.filename:
                raise ValueError("Unsafe Gradle archive path")
        home = directory / name
        if not (home / "bin/gradle").is_file():
            bundle.extractall(directory)
            (home / "bin/gradle").chmod(0o755)
    result = {"gradle_home": str(home.resolve()), "version": GRADLE_VERSION, "source": url, "sha256": GRADLE_SHA256}
    (directory / "gradle.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def bootstrap_maven(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    name = "apache-maven-" + MAVEN_VERSION
    url = "https://archive.apache.org/dist/maven/maven-3/" + MAVEN_VERSION + "/binaries/" + name + "-bin.tar.gz"
    archive = directory / (name + "-bin.tar.gz")
    if not archive.exists():
        temporary = archive.with_suffix(".download")
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open("wb") as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 50 * 1024 * 1024:
                    raise ValueError("Maven download exceeds size limit")
                output.write(chunk)
        temporary.replace(archive)
    if hashlib.sha512(archive.read_bytes()).hexdigest() != MAVEN_SHA512:
        raise ValueError("Maven distribution does not match the pinned vendor checksum")
    home = directory / name
    with tarfile.open(archive) as bundle:
        if any(PurePosixPath(n).is_absolute() or ".." in PurePosixPath(n).parts or not PurePosixPath(n).parts or PurePosixPath(n).parts[0] != name for n in bundle.getnames()):
            raise ValueError("Unsafe Maven archive path")
        if not (home / "bin/mvn").is_file():
            if not hasattr(tarfile, "data_filter"):
                raise RuntimeError("Use a Python security release providing tarfile.data_filter")
            bundle.extractall(directory, filter="data")
    result = {"maven_home": str(home.resolve()), "version": MAVEN_VERSION, "source": url, "sha512": MAVEN_SHA512}
    (directory / "maven.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    main()
