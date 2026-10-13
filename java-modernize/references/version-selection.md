# Version selection and freshness

Re-check versions when the skill runs. This file deliberately contains no frozen
"latest version" catalog. Even without changing Java, JDK patch releases can update
security, certificates, locale/time-zone data, and behavior.

## Select a coherent tuple

Record per module/source set: build JVM, wrapper, compiler/toolchain JDK, `--release`
or equivalent API/bytecode target, framework/platform, test engines and runner,
processors/bytecode tooling, and production runtime/image. The candidate must satisfy
all of these, plus OS/architecture/native requirements and the project's support policy.

1. Find the version owner: root parent, imported BOM, Gradle platform/catalog,
   convention plugin, dependency constraint, lockfile, CI workflow, or image definition.
2. Discover published stable candidates from that component's repository metadata or
   release feed. Maven metadata's `latest`/`release` values may include prereleases;
   check project-specific qualifiers and release notes, not a universal sorting rule.
3. Verify requirements and supported ranges against version-specific official docs.
   Check support status separately; compatible and supported are different claims.
4. Check relevant migration notes and advisories, including transitive dependencies.
   Prefer the newest supported compatible line within the user's constraints. If only
   unsupported choices remain, report this rather than declaring them fully modernized.
5. Resolve the actual dependency/plugin graph and validate the selected tuple locally.
   Record exact versions, evidence URLs, and retrieval date in the report. Distinguish
   vendor-declared support from merely observed test success.

"Stay on Java 17" fixes the feature/API target, not necessarily its patch version.
It also excludes dependencies needing a newer runtime. "Patch-only" fixes component
release lines too. SemVer-looking versions do not guarantee behavior preservation.
Respect exact pins, enterprise mirrors, vendor distributions, and explicit exceptions.

## Evidence order and limits

Use maintainers' compatibility tables, release notes, migration guides, and security
advisories first. Registry metadata establishes publication/existence, not support.
Use a vendor policy for JDK update availability, licensing, and support duration; LTS
is a vendor support designation, not a Java language capability. Do not predict future
GA versions or universal non-LTS lifetimes from a schedule alone.

A library released **before** a JDK's GA may support it (including testing against EA
builds). A later release may still not support it. Release chronology is a reason to
investigate bytecode-sensitive tooling, never a compatibility test.

If a minimum supported version is not documented, say so; choose a current supported
candidate with evidence rather than inventing a minimum. Cite version-specific sources
where possible; rolling documentation can describe a different release tomorrow.
Cross-check a contradictory table against actual release notes and test evidence.

Offline/private-repository fallback: use local resolved metadata to explain present
state, label freshness unverified, and list the exact sources/commands needed to finish.
Do not send private dependency coordinates to public services without authorization.

## Primary discovery entry points

These are entry points, not compatibility claims for arbitrary versions:

| Area | Source |
| --- | --- |
| JDK releases/features | [OpenJDK projects](https://openjdk.org/projects/jdk/), target-version Oracle/OpenJDK release notes |
| Vendor support | [Oracle roadmap](https://www.oracle.com/java/technologies/java-se-support-roadmap.html), [Temurin support](https://adoptium.net/support/) or chosen vendor policy |
| Maven artifacts | [Maven Central](https://central.sonatype.com/), project's configured trusted repository and `maven-metadata.xml` |
| Gradle JVM compatibility | [Gradle matrix](https://docs.gradle.org/current/userguide/compatibility.html) and selected-version docs |
| Maven/toolchain | [Maven releases](https://maven.apache.org/docs/history.html), [compiler plugin](https://maven.apache.org/plugins/maven-compiler-plugin/) |
| Spring | [Boot requirements](https://docs.spring.io/spring-boot/system-requirements.html), [Cloud release trains](https://spring.io/projects/spring-cloud#overview), [support](https://spring.io/projects/spring-boot#support) |
| Tests/bytecode | [JUnit](https://docs.junit.org/current/user-guide/), [Mockito](https://github.com/mockito/mockito/releases), [JaCoCo](https://www.jacoco.org/jacoco/trunk/doc/changes.html), [Lombok](https://projectlombok.org/changelog), [Byte Buddy](https://github.com/raphw/byte-buddy), [ASM](https://asm.ow2.io/versions.html) |
| Security | Maintainer advisories; [GitHub Advisory Database](https://github.com/advisories), [OSV](https://osv.dev/) as cross-checks |
| Recipe catalog | [OpenRewrite](https://docs.openrewrite.org/recipes) and selected recipe's own repository/license |

For products not listed, find their official requirements, release notes, and supported
lines. Lack of an entry does not justify skipping an installed dependency family.
