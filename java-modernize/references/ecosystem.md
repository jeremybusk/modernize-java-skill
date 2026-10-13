# Ecosystem modernization

Apply the relevant sections even when Java stays fixed. Use current, selected-version
requirements and release notes; this is a coverage checklist, not a version matrix.

## Frameworks, platforms, and enterprise APIs

- **Spring Boot / Framework / Security / Cloud:** upgrade the owning Boot parent/BOM
  or plugin and keep framework modules aligned. Match the Cloud release train to the
  Boot line. For major changes follow each official migration guide and its required
  prerequisites; do not combine a JDK change with every optional framework rewrite.
  Check starters, property renames, security configuration, servlet/reactive stack,
  observability, serialization modules, testing support, and packaging/native tooling.
  A properties migrator is a temporary aid, not a runtime dependency to leave forever.
  Boot 3's Jakarta migration and Boot 4's module/library migrations require their own
  guides; Jackson 2→3 is not a version-only edit.
- **Quarkus / Micronaut:** update the platform/BOM and build plugin coherently; verify
  extensions, processors, native image support, and the selected Java/runtime floor.
  Use their official update tools only if applicable and inspect the generated diff.
- **Jakarta EE / MicroProfile / application servers:** align API level, implementation,
  deployment server, descriptors, service registrations, generated code, and clients.
  An API JAR alone does not provide a server or runtime implementation. Jakarta EE 8
  retained `javax`; EE 9 moved the affected EE APIs to `jakarta` with compatibility
  breaks. Java SE packages such as `javax.sql`, `javax.crypto`, `javax.net`, and
  `javax.xml.parsers` remain `javax`. Map each affected specification explicitly.
- **Persistence:** inspect Hibernate/JPA/provider compatibility, proxying, dialects,
  sequences, query behavior, converters, validation, Flyway/Liquibase modules, JDBC
  drivers, and supported database/server versions. Test real database behavior using
  the existing integration setup. Do not run a production schema migration as a test.

Sources: [Boot migration guides](https://github.com/spring-projects/spring-boot/wiki),
[Cloud](https://spring.io/projects/spring-cloud),
[Quarkus updating](https://quarkus.io/guides/update-quarkus),
[Micronaut](https://docs.micronaut.io/latest/guide/),
[Jakarta EE 9](https://jakarta.ee/specifications/platform/9/jakarta-platform-spec-9.html),
[Hibernate](https://hibernate.org/orm/releases/).

## Libraries and version owners

Inspect both declared and resolved dependencies. Include managed, transitive, shaded,
generated, and agent dependencies where they affect the application.

| Family | Checks that ordinary version bumps can miss |
| --- | --- |
| Jackson / JSON-B / Gson | JSON shape, dates/nulls/naming, polymorphism, module coordinates and major-version APIs |
| Logging: SLF4J / Logback / Log4j | API/provider generation, multiple bindings, bridges/loops, config changes and appenders |
| HTTP: JDK client / Apache / OkHttp / Netty | TLS/auth/proxy behavior, timeouts, connection/resource ownership, native transports |
| Commons / Guava / Caffeine | Removed APIs, null/mutability contracts, Java floor and eviction/concurrency behavior |
| JDBC / database clients | Server compatibility, driver class/artifact, TLS/auth/time-zone behavior, native/OS support |
| Messaging: Kafka / JMS / AMQP / Redis clients | Broker compatibility, serializers, retries, delivery/ordering, transactions and backpressure |
| gRPC / Protobuf / codegen | Compiler/runtime/plugin compatibility, generated API and wire compatibility |
| Cloud SDKs / telemetry agents | SDK major versions, credentials/retries, transport, agents and framework integration |

Upgrade the platform owner first when it supplies a tested set. A vulnerability override
may be appropriate, but record the advisory and constraint, validate the deviation, and
remove it when the platform catches up. Do not replace one framework/client with another
merely because an upstream example prefers it.

## Tests, processors, bytecode tools

- **JUnit / TestNG:** verify engines/extensions, Java test-runtime floor, Surefire/
  Failsafe or Gradle platform configuration, parameterization, tags, disabled tests,
  and test counts. JUnit 6 needs Java 17+ for tests; it can test code targeting older
  Java. Maintaining Java 11 production does not automatically authorize moving all
  tests to Java 17 or dropping minimum-runtime validation. Vintage is a temporary
  migration bridge; do not silently exclude remaining JUnit 3/4 tests.
- **Mockito / PowerMock / Byte Buddy:** verify mock maker, agents, dynamic-attach
  restrictions, bytecode level, native-image limitations, and legacy runners.
  Removing PowerMock can require refactoring the affected tests and seams.
- **JaCoCo / ASM / Javassist / agents:** distinguish official support for a class-file
  version from experimental support. Upgrade the owner bringing a stale transitive
  bytecode library before forcing an isolated dependency override.
- **Lombok / MapStruct / processors / Kotlin:** verify actual compiler-JDK support,
  processor configuration, generated code, module paths, and mixed-language targets.
- **Static analysis / formatters / generators:** check SpotBugs, Checkstyle, Error
  Prone, PMD, Javadoc, JAXB/WSDL/Protobuf generators and packaging plugins when present.
  A compiler can support a syntax level that a formatter or analyzer cannot parse.

Sources: [JUnit guide](https://docs.junit.org/current/user-guide/),
[Mockito](https://github.com/mockito/mockito),
[JaCoCo changes](https://www.jacoco.org/jacoco/trunk/doc/changes.html),
[Lombok changelog](https://projectlombok.org/changelog),
[MapStruct](https://mapstruct.org/documentation/).

## CI, containers, and ongoing maintenance

Inspect setup-java/actions and wrapper versions, CI runner/runtime compatibility,
version-manager configuration, JDK distribution/patch levels, buildpacks/Jib/Docker,
base OS packages, image digests/tags, CPU architecture, and existing JVM flags.
Build and run stages can require different images; a JRE or custom `jlink` runtime is
appropriate only when it contains the modules, diagnostics, and agents actually needed.
Switching glibc→musl, architecture, or vendor is a separate compatibility change.
Coordinate scanner findings for application dependencies and OS/base-image packages.

Use existing vulnerability/SBOM tooling if available. Check advisory database freshness,
affected ranges and false positives; preserve justified suppressions and revisit them.
Scanner errors or unavailable metadata mean incomplete checks. Never suppress a real
finding solely to make validation pass. SBOMs and scanned JARs should reflect the resolved
packaged application, not just direct dependencies in a source manifest.

For requested recurring maintenance, configure the existing Renovate or Dependabot
workflow with schedules, platform/grouping rules, support constraints, prerelease
exclusions, CI, and major-upgrade handling. Image and CI-action updates are separate
managers/ecosystems. Avoid competing update bots. Do not enable automatic merging or
create scheduled external jobs unless authorized.

Sources: [Renovate Java](https://docs.renovatebot.com/java/),
[Renovate Docker](https://docs.renovatebot.com/docker/),
[Dependabot options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference),
[Dependency-Check](https://jeremylong.github.io/DependencyCheck/).
