#!/usr/bin/env python3
"""Download a pinned Linux x64 test JDK into a temporary tool directory."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request


# Historical integration tuple, not the skill's recommendation of a latest JDK.
LOCKS = {
    "25": ("25.0.4+7", "https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4%2B7/OpenJDK25U-jdk_x64_linux_hotspot_25.0.4_7.tar.gz", "e58fcdcd637b25c03ca84cbbcefc70d11efb8f4b4cbd05decc9f661769d77f94"),
    "8": ("8u504-b01", "https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u504-b01/OpenJDK8U-jdk_x64_linux_hotspot_8u504b01.tar.gz", "9c70e102f527ac674ac2fe9c7d47b9a04e2d19842ba5ab8e9b33f368bbadfaea"),
}


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
    args = parser.parse_args()
    print(json.dumps(bootstrap(args.directory, args.jdk_feature), indent=2))


if __name__ == "__main__":
    main()
