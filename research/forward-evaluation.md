# Independent forward evaluation of java-modernize

Checked: 2026-10-12. Skill: `/src/jupgrade-skill/java-modernize/SKILL.md`.
Inputs: the four raw files under `/tmp/java-modernize-forward-fixtures`.
The following are the actual audit deliverables, followed by evaluation findings.
Project files and the skill were not edited. No build was executed and nothing was installed.

## Audit A — Java 11 public library

Request: audit available maintenance updates, including tests; retain Java 11 support in production and tests; no edits.

### Scope and observed baseline

`library/pom.xml` declares `maven.compiler.release=11`, `junit.version=5.11.0`, and test-scoped `org.junit.jupiter:junit-jupiter`. The property owns that dependency version. There is no declared parent, compiler plugin, test plugin, wrapper, toolchain, CI, source, or test code in the supplied fixture.

Preserve Java 11 as the production and test runtime minimum and as the compilation/API target. The Maven build JVM, actual compiler JDK, test JVM, current JDK patch/vendor, Maven version, effective lifecycle plugin versions, and resolved dependency graph are unknown. A declared release property alone does not prove the effective compiler plugin uses it. Test discovery is also unverified.

### Version evidence and recommendations

All sources in this table were checked on 2026-10-12. Candidates are proposals requiring real-project resolution and execution.

| Component / owner | Current declared → resolved | Selected candidate | Reason and limits | Primary evidence |
| --- | --- | --- | --- | --- |
| JUnit Jupiter / `junit.version` in POM | 5.11.0 → unresolved | 5.14.4 | Latest Java-11-compatible JUnit 5 release observed in upstream release listing. The version-specific guide requires Java 8+, so Java 11 tests remain viable. Align Jupiter and Platform through its transitive graph or a JUnit BOM if the full project uses other JUnit artifacts. | [5.14.4 release](https://github.com/junit-team/junit-framework/releases/tag/r5.14.4), [5.14.4 requirements](https://docs.junit.org/5.14.4/overview.html) |
| Latest JUnit line / excluded candidate | Not installed | 6.1.3 excluded | Upstream lists 6.1.3 as latest, but its Java 17 test-runtime minimum conflicts with the explicit Java 11 test constraint. | [Upstream releases](https://github.com/junit-team/junit-framework/releases), [6.1.3 requirements](https://docs.junit.org/6.1.3/overview.html) |
| Compiler plugin / Maven lifecycle default unless made explicit | Undeclared → unknown | 3.16.0, conditional | Official plugin docs show this stable version and Maven 3.6.3 / Java 8 minimums. Resolve the existing effective version first, then propose an explicit pin if appropriate. Retain release 11 for main and test compilation. The 4.0 beta line is excluded from stable maintenance. | [Compiler plugin requirements](https://maven.apache.org/plugins/maven-compiler-plugin/plugin-info.html) |
| Surefire / Maven lifecycle default unless made explicit | Undeclared → unknown | 3.5.6 as conservative candidate; newest overall line remains to assess | Version-specific docs require Maven 3.6.3 and Java 8. Current docs also advertise 3.6.0 with changed provider behavior; that plugin's JVM floor alone does not establish all its resolved test-engine/provider runtime requirements. Verify the actual runner graph and test counts on Java 11 before selecting the newer line. | [3.5.6 requirements](https://maven.apache.org/surefire-archives/surefire-3.5.6/maven-surefire-plugin/plugin-info.html), [3.6.0 provider changes](https://maven.apache.org/surefire/maven-surefire-plugin/examples/junit-platform.html) |
| Java 11 patch / vendor unspecified | Feature 11 required; patch unresolved | No vendor change selected | Refresh the existing vendor's supported Java 11 patch. If the project already uses Temurin, the latest published release endpoint observed is 11.0.32.1+1. Do not infer the project uses Temurin or select the roadmap's planned October build as already published. | [Published Temurin 11 release](https://github.com/adoptium/temurin11-binaries/releases/tag/jdk-11.0.32.1+1), [vendor support policy](https://adoptium.net/support/) |

JUnit 5.14.4 is a compatible maintenance candidate, but this check did not establish a future support commitment for JUnit 5. Publication and Java compatibility are distinct from continuing support.

### Prioritized follow-up

1. Establish actual Maven, compiler, and Surefire versions and confirm main/test output targets Java 11. The absent wrappers and tools are audit limitations; do not manufacture them for this partial fixture.
2. Propose the JUnit property update together with a compatible test runner, then execute the full project's tests on Java 11 and compare discovery, execution, and skipped counts. Keep any engines found in the real project until their tests are migrated.
3. Check the actual JDK vendor patch, direct/transitive advisories, packaging, and a Java 11 consumer smoke test. No vulnerability finding is established by the supplied POM alone.

When operating on the full project with permission to execute its existing build, inspect its wrapper/version command, effective POM, dependency tree, and existing verification command. Such commands were **not run** here. Baseline build/tests, artifact API/bytecode inspection, dependency resolution, security scanning, and production-runtime validation are **not run**, not passing. Static inventory was **passed**. No project files changed.

## Audit B — application with separate compiler and deployment targets

Request: audit modernization while retaining declared compilation and deployment targets; include dependency/tooling freshness and appropriate Java idioms; no edits.

### Scope and observed baseline

`application/build.gradle.kts` selects compiler/toolchain Java 21 and applies `options.release=17` to every `JavaCompile` task, including normal test compilation tasks. The deployment Dockerfile declares `eclipse-temurin:17-jre`. Preserve all three: compiler feature 21, compilation/API/bytecode target 17, and production runtime feature 17. The JVM running Gradle is undeclared. The Java plugin normally derives test launchers from its toolchain, making Java 21 a likely default test JVM, but actual test execution is unverified; no tests or launch configuration are supplied.

The Spring Boot plugin and explicitly imported Boot BOM both declare 3.5.0. The BOM owns the version of `spring-boot-starter-web` and its managed application libraries. Their effective resolutions remain unknown. The fixture has no wrapper, settings file, dependency repositories, locks, or test infrastructure. `Samples.java` is at the fixture root rather than a standard source directory; actual inclusion in the project build is unknown. The single-line Dockerfile is a runtime-target clue, not a complete executable application image.

### Version evidence and recommendations

All sources below were checked on 2026-10-12. Do not interpret an update proposal as a successfully tested tuple.

| Component / owner | Current declared → resolved | Selected candidate | Reason and limits | Primary evidence |
| --- | --- | --- | --- | --- |
| Spring Boot plugin and BOM / both literals in Gradle file | 3.5.0 → unresolved | 3.5.16 as same-line candidate | Version-specific upstream docs and an upstream release establish existence and Java 17 minimum; Java 21 compiler and Java 17 runtime fit the documented range. Update plugin and BOM together. Its current OSS support status remains unverified, so this is not a claim that staying on 3.5 yields a currently supported platform. | [3.5.16 release](https://github.com/spring-projects/spring-boot/releases/tag/v3.5.16), [3.5 requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html) |
| Newer Boot major / separate migration opportunity | Not installed | No major selected | Current Spring project and documentation show 4.1.1 as latest stable. A major migration needs its own module/library migration assessment; unchanged Java does not make it a version-only update. Support status may make that follow-up important. | [Boot project](https://spring.io/projects/spring-boot/), [Boot requirements entry point](https://docs.spring.io/spring-boot/system-requirements.html) |
| Starter web and managed libraries / imported BOM | Starter unversioned → unresolved | Managed set from selected BOM | Review the resolved web/JSON/logging/container graph after updating the BOM rather than independently assigning unrelated latest versions. Security and compatibility require the actual packaged graph. | [3.5.16 release](https://github.com/spring-projects/spring-boot/releases/tag/v3.5.16) |
| Gradle / wrapper absent | Undeclared → unknown | 8.14.4 as verified compatible example, not proven newest 8.x | Boot 3.5 docs specify supported Gradle 7/8 ranges. Gradle's matrix requires 8.4+ for a Java 21 toolchain and 8.5+ if Java 21 runs Gradle. 8.14.4 has official release notes and fits both; first identify the actual build version and its plugins. Current Gradle 9 releases should not be automatically selected against Boot 3.5's documented build-support ranges. | [Gradle 8.14.4 release](https://docs.gradle.org/8.14.4/release-notes.html), [JVM matrix](https://docs.gradle.org/current/userguide/compatibility.html), [Boot build support](https://docs.spring.io/spring-boot/3.5/system-requirements.html) |
| Java 21 compiler patch / vendor unspecified | Feature 21; patch unresolved | Existing vendor's supported Java 21 patch | If already Temurin, observed published candidate is 21.0.12.1+1. Preserve the feature level and verify the actual compiler selection. | [Temurin 21 release](https://github.com/adoptium/temurin21-binaries/releases/tag/jdk-21.0.12.1+1) |
| Deployment image / Dockerfile | `17-jre` floating tag → image/digest unknown | No exact image digest selected | Latest published Temurin Java 17 binary observed is 17.0.20.1+1. Binary publication does not prove a matching image has been built for the required OS/architecture. Verify the actual registry manifest and runtime patch, then select an exact supported Java 17 image/digest. Keep the current vendor/OS/architecture constraints. | [Temurin 17 binary](https://github.com/adoptium/temurin17-binaries/releases/tag/jdk-17.0.20.1+1), [official container update policy](https://github.com/adoptium/containers) |

The support link on Spring's project page returned no extracted support table in this session. The older supported-versions wiki supplies a policy but not sufficient current line-status evidence. Confirm current OSS/commercial support before calling the chosen Boot line supported.

### Concrete source opportunities

`Samples.names()` immediately mutates the collected list with `result.add("extra")`. Java 17 supports `Stream.toList()`, but substituting it would make that call throw `UnsupportedOperationException`. A suitable optional change is making the required mutable collection explicit:

```java
List<String> result = input.collect(Collectors.toCollection(ArrayList::new));
```

This preserves mutability, encounter order, and null acceptance without requiring a newer API target. Check callers for concrete implementation assumptions before changing code. The unmodifiable-result contract is documented in the [Java 17 Stream API](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/stream/Stream.html).

`empty(String)` could use Java 11's `isBlank()` only if the desired contract uses `Character.isWhitespace`. It is not behavior-preserving for arbitrary inputs: `trim().isEmpty()` treats every character at or below U+0020 as removable, while `isBlank()` uses Java whitespace classification. For example, `"\u0000"` changes from true to false; `"\u2003"` changes from false to true. Keep existing behavior unless requirements authorize the broader semantic change, then add focused boundary cases in the real project. See [Java 17 String API](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/String.html).

`javax.sql.DataSource` is a Java SE API in module `java.sql`; retain its namespace. A blanket `javax` to `jakarta` rewrite would be incorrect here. See [Java 17 DataSource API](https://docs.oracle.com/en/java/javase/17/docs/api/java.sql/javax/sql/DataSource.html).

Java 21 virtual threads, pattern switch, and sequenced collection APIs exceed the declared release 17 target even though the compiler JDK is 21. They are excluded from this audit's source recommendations. No record conversion or architecture migration is justified by this small class.

### Prioritized follow-up and validation

Resolve current Boot support status and the actual Gradle build tuple first. Then propose one coherent plugin/BOM update, inspect the resolved and packaged dependency graph/advisories, refresh compatible JDK patches and the Java 17 image, and evaluate the small mutable-list clarification. Keep the whitespace method unchanged pending an explicit behavior requirement.

For the complete project, use its existing Gradle wrapper and tasks to inspect versions/dependencies and run builds/tests. Include application startup on the Java 17 deployment image, not merely compilation/tests on Java 21. No wrapper, repositories, Docker copy/entry point, sources layout, or tests were added. Static inventory was **passed**; build, test discovery/counts, dependency resolution, image manifest verification/scanning, and application startup are **not run**. No project files changed.

## Evaluation findings and limitations

- Both requests reached actionable audit outputs without changing projects, installing tools, or running absent builds. The helper found all three configuration files, deliberately omitted Java source from its configuration inventory, and explicitly reported that effective versions were not resolved. Direct source inspection supplied the idiom analysis.
- The resulting audits preserved the explicit Java 11 test constraint, separately represented build/compiler/API/test/deployment JVMs, kept BOM ownership, avoided introducing Java 21 features under release 17, protected list mutability and whitespace semantics, and retained the Java SE `javax.sql` namespace.
- No observable skill defect was demonstrated by these two audits. Some outcomes required agent judgment and live browsing; the skill cannot resolve missing infrastructure or make inaccessible registry/support metadata available.
- Raw Maven metadata endpoints were unavailable through the browsing tool, search results were sometimes older than directly opened maintainer pages, and Spring support-page extraction did not expose current status. The audits explicitly separate observed published candidates, compatibility evidence, support uncertainty, and untested effective graphs. They do not claim exhaustive latest-version discovery or runtime verification.
- This is one independent agent pass on two intentionally partial fixtures. It validates constrained audit behavior, not implementation quality across full Maven/Gradle builds, automated recipes, other agents' discovery behavior, or successful execution of all proposed candidate tuples.
