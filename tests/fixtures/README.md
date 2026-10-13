# Complete migration fixtures

These are controlled public examples, not an external production application or a
general migration engine. Each full scenario copies its fixture into a fresh temporary
directory and performs baseline build/tests/startup, a scoped migration, verification,
and a final rerun with unchanged source/configuration.

- `maven-java8`: a real two-module reactor, JUnit tests and packaged application,
  executed first on Java 8 and then Java 25. Compression round trips exercise resource
  cleanup and a stable wire-data contract; class-file levels are checked in both stages.
- `spring-boot`: a real executable HTTP application and context/mock test. Separate
  scenarios cover Boot 3.5.15→3.5.16 while retaining release 17 and a Boot 3.5→4.0
  migration with `@MockBean` replacement and preserved HTTP response shape.
- `gradle-catalog`: equivalent Groovy/Kotlin DSL builds with a centrally owned JUnit
  BOM/catalog, real dependency locks, tests and application startup. Maintenance uses
  a scoped manual catalog change and Gradle-native lock regeneration; it does not
  claim OpenRewrite Gradle-plugin execution was tested.

Historical dependency/recipe versions are deliberately pinned fixture inputs, not
the skill's latest-version advice. Current requirements and source checks are recorded
in [integration-sources.md](../../research/integration-sources.md).

OpenRewrite composite transformations can require a fresh parse after changing the
effective target. The harness bounds stabilization to four passes, validates the result,
and then separately requires a final no-op rerun. Unexpected oscillation or lost tests
fails the scenario.

Maven receives synthetic empty user/global settings, local fixture installs stay in
the selected temporary repository, and Gradle uses a separate user-home directory.
Inherited application configuration and Java/Gradle/Maven injection flags are removed
only from fixture subprocesses. No remote artifact publication or production deployment
is performed. Boot HTTP requests bind/connect only to loopback.
