# Inventory and build configuration

## Inventory beyond the visible build file

Inspect Maven reactors/parents/profiles, Gradle included builds/`buildSrc`/convention
plugins/version catalogs, dependency locks and verification metadata, toolchain files,
CI matrices, image definitions, runtime flags, and deployment manifests.
Include tests, processors, plugins, generated code, shaded JARs, and Java agents.
Do not edit generated outputs when their inputs/generator own the change.

The optional `scripts/inventory.py` produces paths and line evidence only. It ignores
generated/cache directories and symlinks; reports skipped/unreadable configurations.
Its text matches can include comments and miss dynamic logic. No signal is a selected
or effective version. It is a starting point, not a parser for Maven/Gradle semantics.

Use existing wrappers; a build is executable project code. Do not run publishing,
release tasks, or migrations against external databases during inventory. Effective
models are valuable when build execution is permitted:

```sh
./mvnw -version
./mvnw help:effective-pom -Doutput=target/effective-pom.xml
./mvnw dependency:tree -Dverbose
./mvnw versions:display-dependency-updates
./mvnw versions:display-plugin-updates
./mvnw versions:display-parent-updates
./gradlew --version
./gradlew projects
./gradlew :app:dependencies --configuration runtimeClasspath
./gradlew :app:dependencyInsight --dependency <name> --configuration runtimeClasspath
```

Adapt module/configuration names and profiles to the project. Versions goals require
the [Versions plugin](https://www.mojohaus.org/versions/versions-maven-plugin/);
configure or invoke a verified pinned plugin version if needed. Such goals discover
updates, not their correctness. Inspect compile/test/processor classpaths too.
Gradle has no universal built-in `dependencyUpdates` task; only invoke it if the
project uses a corresponding plugin, or inspect verified metadata directly.
Sanitize build diagnostics before including them in a public report.

## Maven

- Prefer the existing configuration owner. A Boot parent may own compiler/test plugin
  versions and use `java.version`; an imported BOM manages dependencies but does not
  supply parent plugin management. Do not add redundant child overrides everywhere.
- `--release` restricts the language, bytecode, and available platform APIs; `source`
  and `target` alone do not provide the same API guarantee. Verify compiler-plugin
  behavior and the JDK's supported historical releases. Maven compiler plugin 3.13+
  can translate `release` to source/target on JDK 8; that does not create JDK 9's API
  checking capability on JDK 8. Avoid a universal "release requires JDK 9" rule.
- Separate the JVM running Maven from compiler/test toolchains. Read `toolchains.xml`
  as needed without exposing machine-specific credentials or paths.
- Check compiler, Surefire/Failsafe, JaCoCo, Enforcer, Javadoc, shading/packaging,
  code generation, static analysis, and framework plugins that are actually present.
- JDK 23 changed annotation-processing defaults: explicitly declare processors and
  appropriate configuration for the chosen Maven/compiler-plugin version. Do not
  compensate with indiscriminate processor scanning of arbitrary dependencies.

Sources: [release option](https://maven.apache.org/plugins/maven-compiler-plugin/examples/set-compiler-release.html),
[annotation processors](https://maven.apache.org/plugins/maven-compiler-plugin/examples/annotation-processor.html),
[toolchains](https://maven.apache.org/guides/mini/guide-using-toolchains.html).

## Gradle

- Verify two distinct matrix columns: JDKs usable as **toolchains** and JDKs that can
  **run Gradle**. A supported compiler does not imply a supported daemon JVM.
- Configure toolchains and `options.release` where the API target differs from the
  compiler. `sourceCompatibility`/`targetCompatibility` do not select a JDK.
- Inspect JVM settings for tests, Java/Kotlin mixed builds, KAPT/KSP, Kotlin JVM
  targets, settings plugins, catalogs, platforms, constraints, and dependency locks.
- Use the wrapper upgrade task/procedure for the selected supported version and
  review wrapper files and distribution checksum. Some upgrades require a second
  wrapper invocation to refresh scripts/JAR; follow the selected release's guide.
- Update locks/checksums intentionally via existing tooling; never delete verification
  metadata to permit an unverified artifact. Check removed APIs when crossing Gradle
  majors and the compatibility of convention and framework plugins.

Sources: [matrix](https://docs.gradle.org/current/userguide/compatibility.html),
[toolchains](https://docs.gradle.org/current/userguide/toolchains.html),
[wrapper upgrades](https://docs.gradle.org/current/userguide/gradle_wrapper.html#sec:upgrading_wrapper),
[dependency locking](https://docs.gradle.org/current/userguide/dependency_locking.html),
[verification](https://docs.gradle.org/current/userguide/dependency_verification.html).
