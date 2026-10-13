# Design, upstream comparison, and corrections

Reviewed repository snapshots on 2026-10-12. Commit IDs below identify the actual
sources inspected; they do not imply the source repositories remain at those revisions.

| Source / revision | Useful contribution | Treatment in the combined skill |
| --- | --- | --- |
| [G10xy/java-version-upgrade-skill](https://github.com/G10xy/java-version-upgrade-skill/tree/7c043a00d46bcf2997fd7cc4da6447900e562f00) — Apache-2.0 | Numbered audit/build/refactor/validate workflow, runtime vs language target, cumulative migration boundaries, silent behavior changes | Structural foundation, rewritten and expanded to cover maintenance; no copied frozen dependency-minimum matrix |
| [brunoborges/javaevolved](https://github.com/brunoborges/javaevolved/tree/7beda13f675d84f3fa6781ed6dd06f144349b6cc) — MIT | Before/after patterns and current `modern-java` plugin's compilation-target/preview awareness | Selected final-feature coverage and contract-aware pattern guidance; avoid importing the entire site, translations, detector binary, or catalog |
| [darshitpp/java-code-upgrade](https://github.com/darshitpp/java-code-upgrade/tree/938c3f720612a40f60146e2aeea4a5e6b7372ca2) — MIT | Search-driven patterns, categories, scoped lookup and before/after reporting | Pattern search and contextual review; replace difficulty-based "drop-in" assumptions with contract checks |
| [microsoft/modernize-java agent](https://github.com/microsoft/modernize-java/blob/b02350dad12888d3064c07c58fd1cc407e0c7b6f/plugins/modernize-java/com.github.copilot/agents/modernize-java.agent.md) — repository MIT | Incremental plans, preserve CVE overrides, wrapper preference, baseline/result validation, concrete summary | High-level principles incorporated; no copied internal prompts, MCP/backend requirement, telemetry hooks, session lifecycle, forced Spring conversion or automatic version-control mutations |

The user preferred G10xy's format, so the new skill retains a numbered workflow with
focused supporting references. The other projects add code-pattern and execution
ideas. A direct concatenation would preserve conflicting exclusions and duplicate
instructions: G10xy excludes same-Java refactors and framework migrations; the requested
skill must handle both. Microsoft's plugin is a useful alternative for users already
working in its Copilot environment, but its mandatory tools do not form a portable core.

## Decisions

- **One portable skill, four composable modes:** audit, upgrade Java, maintain current
  Java, and modernize code. Ordinary modernization preserves the current Java target
  unless a broader upgrade is requested.
- **Freshness as execution-time evidence:** candidates are checked from official
  metadata and version-specific support/requirements, then constrained by the actual
  platform/runtime. No permanently asserted "latest" or guessed minimum table.
- **Version owners:** use parents/BOMs/catalogs/conventions and resolved dependency
  graphs. Include wrappers/plugins/processors/tests/images even without a JDK change.
- **Behavior-preserving defaults:** architectural migrations and preview features are
  separate decisions. No automatic SOAP→REST, JDBC→ORM, or runnable-app→Spring Boot.
- **Optional automation:** OpenRewrite and Microsoft tools can help when available;
  verified artifacts/access and normal validation remain necessary. No required agent-
  specific tools or telemetry.
- **Small deterministic helper:** inventory only; avoids falsely "detecting" a single
  effective Java version from incomplete static configuration. It emits paths/line
  numbers, not raw values, and needs only Python 3. Manual inventory remains possible.

## Corrections backed by primary sources

| Upstream claim or risky implication | Correction / evidence |
| --- | --- |
| A library released before a JDK's GA cannot support that JDK | Chronology cannot prove incompatibility. JaCoCo release notes explicitly distinguish official and experimental support for future Java releases; verify actual declared support and tests. [JaCoCo release history](https://www.jacoco.org/jacoco/trunk/doc/changes.html) |
| Finalization removed in Java 21 | Deprecated for removal since 18, still in Java 25. [Java 25 deprecated list](https://docs.oracle.com/en/java/javase/25/docs/api/deprecated-list.html) |
| Structured concurrency/stable values/PEM are ordinary Java 25 upgrades | These APIs are preview in 25; scoped values are final. Verify exact target, not a catalog's numeric minimum alone. [Preview list](https://docs.oracle.com/en/java/javase/25/docs/api/preview-list.html), [ScopedValue](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ScopedValue.html) |
| Java 25 structured concurrency using `new StructuredTaskScope.ShutdownOnFailure()` | Java 25 uses the revised interface/static-open/joiner API. Do not adopt older preview examples as target-25 code. [API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/StructuredTaskScope.html) |
| `synchronized` always pins virtual threads | Monitor pinning was addressed in Java 24; native/foreign pinning can remain. Avoid unnecessary lock rewrites on 24+. [Virtual-thread guide](https://docs.oracle.com/en/java/javase/25/core/virtual-threads.html) |
| `List.of`, records, `Stream.toList`, or `isBlank` are universally drop-in | Mutability/null policy, accessors/framework contracts, shallow immutability, and whitespace definitions can change behavior. [List](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/List.html), [Stream](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Stream.html), [records](https://docs.oracle.com/en/java/javase/25/language/records.html), [String](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/String.html) |
| Every `javax` import becomes `jakarta` | Only the migrated EE specifications do; Java SE still includes many `javax` APIs. [Jakarta EE 9](https://jakarta.ee/specifications/platform/9/jakarta-platform-spec-9.html), [Java SQL](https://docs.oracle.com/en/java/javase/25/docs/api/java.sql/module-summary.html), [Java XML](https://docs.oracle.com/en/java/javase/25/docs/api/java.xml/module-summary.html) |
| Gradle support is one minimum for a Java release | Toolchain and daemon-JVM support have distinct matrix columns. [Gradle compatibility](https://docs.gradle.org/current/userguide/compatibility.html) |
| Classpath arguments automatically scan every third-party JAR | Supply explicit artifacts or documented traversal and inspect coverage; static tools also miss reflection. [jdeps](https://docs.oracle.com/en/java/javase/25/docs/specs/man/jdeps.html), [migration preparation](https://docs.oracle.com/en/java/javase/25/migrate/preparing-migration.html) |
| Current OpenRewrite migration binaries are always publicly available on Maven Central | Verify artifact/version repository, license, and access. The live migration guide documents source-available/access changes. [Recipe guide](https://docs.openrewrite.org/running-recipes/popular-recipe-guides/migrate-to-java-17) |

Detailed ecosystem verification, live release observations, and caveats are in
[verified-ecosystem.md](verified-ecosystem.md). The shipping skill uses dynamic selection
instead of carrying those snapshot versions forward as timeless defaults.

## What remains outside this deliverable

This is a reusable skill package, not a tested migration of a particular production
application. Downstream agents still need the project, its constraints, current metadata,
toolchains, and validation environment. Offline runs cannot establish freshness. The
optional inventory helper does not parse or evaluate build semantics. Public distribution,
installation into personal agent directories, and external bot scheduling were not performed.
