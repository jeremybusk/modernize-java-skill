# Primary sources for real modernization integrations

Verified 2026-10-12. This note verifies published metadata, recipe definitions, and supported version ranges; it does not claim that any build or migration was executed. Fixture designs below are recommendations inferred from those sources.

## Supported tuples

| Scenario | Recommended tuple | Evidence and limitation |
| --- | --- | --- |
| Plain Java 8 → 25, Maven | Java 8 source/release before migration; target/runtime JDK 25; Maven 3.9.x; `rewrite-migrate-java:3.42.1`; `org.openrewrite.java.migrate.UpgradeToJava25` | The tagged recipe updates Java level and compatible build plugins, includes the Java 21 composite, and includes a concrete `Deflater.end()` → `close()` migration. [Pinned recipe source](https://raw.githubusercontent.com/openrewrite/rewrite-migrate-java/v3.42.1/src/main/resources/META-INF/rewrite/java-version-25.yml). |
| Boot maintenance, unchanged Java | JDK 17 or 21; Boot 3.4.x → 3.4.13; Maven 3.9.x | Boot 3.4.13 supports Java 17–24 and Maven ≥3.6.3. Keep Java explicitly fixed and assert it remains fixed. [Boot 3.4 requirements](https://docs.spring.io/spring-boot/3.4/system-requirements.html). |
| Boot 3.5 patch maintenance, unchanged Java | JDK 17, 21, or 25 fixed before/after; Boot 3.5.15 → 3.5.16; Maven 3.9.x | Spring officially announced 3.5.15 on June 10, 2026 and explicitly states it is available from Maven Central. Use an exact `UpgradeParentVersion` target of 3.5.16. [3.5.15 announcement](https://spring.io/blog/2026/06/10/spring-boot-3-5-15-available-now/), [release tag](https://github.com/spring-projects/spring-boot/releases/tag/v3.5.15), [3.5 requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html). |
| Boot minor migration | JDK 17 or 21; Boot 3.4.13 → 3.5.x; `rewrite-spring:6.37.1`; `org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_5` | Tagged composite upgrades the parent/BOM/dependencies/build plugin using `3.5.x`. Boot 3.5.16 supports Java 17–25. [Pinned recipe](https://raw.githubusercontent.com/openrewrite/rewrite-spring/v6.37.1/src/main/resources/META-INF/rewrite/spring-boot-35.yml), [requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html). |
| Boot major migration | JDK 17 or 21; preferably Boot 3.5.16 → 4.0.x; `rewrite-spring:6.37.1`; `org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0` | The composite includes the 3.5 migration, so it can exercise an earlier 3.4 fixture, but Spring recommends first reaching the newest 3.5 patch. Boot 4.0.8 supports Java 17–26, Maven ≥3.6.3, and Gradle ≥8.14. [Tagged recipe](https://raw.githubusercontent.com/openrewrite/rewrite-spring/v6.37.1/src/main/resources/META-INF/rewrite/spring-boot-40.yml), [Spring migration guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide), [requirements](https://docs.spring.io/spring-boot/4.0/system-requirements.html). |
| Gradle Groovy/Kotlin DSL catalog + locks | Gradle 8.14.3; JDK 17 or 21; Java application sources; JUnit 5.14.4 | Java 25 requires Gradle 9.1+ for both runtime and supported toolchains. Keep these fixtures on Java 17/21 unless the wrapper is also upgraded. A Kotlin build script does not require Kotlin application sources. [Gradle compatibility matrix](https://docs.gradle.org/current/userguide/compatibility.html). |

Do not use unchanged Boot 3.4.13 with target Java 25 as a supported success tuple. Likewise, a Gradle 8.14.3 build executed under JDK 25 would be outside its supported matrix. These are consequences of the official version ranges above.

## Historical public artifacts and runtime alignment

Maven Central's canonical artifact pages currently identify these selected releases and expose their published POMs:

- `org.openrewrite.recipe:rewrite-migrate-java:3.42.1`: Rewrite core/BOM **8.90.2**, including `rewrite-java-25:8.90.2`. [Published metadata](https://central.sonatype.com/artifact/org.openrewrite.recipe/rewrite-migrate-java).
- `org.openrewrite.recipe:rewrite-spring:6.37.1`: Rewrite core/BOM **8.90.2**; transitively references `rewrite-migrate-java:3.42.0` and `rewrite-testing-frameworks:3.44.0`. Supplying migrate-java 3.42.1 explicitly changes that transitive selection. [Published metadata](https://central.sonatype.com/artifact/org.openrewrite.recipe/rewrite-spring).
- `org.openrewrite.maven:rewrite-maven-plugin:6.46.1`: published plugin POM sets Rewrite **8.89.0**. This is publicly indexed, but is not an engine-aligned tuple with the two recipes above. A real execution must establish whether the plugin resolves and runs their newer core APIs correctly; do not infer compatibility solely from cache presence. [Exact plugin metadata](https://central.sonatype.com/artifact/org.openrewrite.maven/rewrite-maven-plugin/6.46.1).
- `org.junit.jupiter:junit-jupiter:5.14.4` and `:6.0.3` have exact public Central pages. JUnit 5 requires Java 8+, whereas JUnit 6 requires Java 17+. Prefer 5.14.4 for a fixture that must genuinely build on Java 8 before migration. [JUnit 5 artifact](https://central.sonatype.com/artifact/org.junit.jupiter/junit-jupiter/5.14.4), [JUnit 6 artifact](https://central.sonatype.com/artifact/org.junit.jupiter/junit-jupiter/6.0.3), [5.14.4 Java support](https://docs.junit.org/5.14.4/overview.html), [6.0.3 Java support](https://docs.junit.org/6.0.3/overview.html).

The current OpenRewrite catalog examples mention plugin 6.50.0 and authenticated Code Genome distribution. The exact 6.50.0 Central page could not be retrieved in this research, so public availability of that plugin version is **not verified**. This is distinct from the verified historical Central metadata above. Avoid `RELEASE`/latest coordinates in a public, reproducible integration harness. [Current Java 25 catalog](https://docs.openrewrite.org/recipes/java/migrate/upgradetojava25).

Boot 3.4.13, 3.5.16, and 4.0.8 are identified by the official versioned requirements pages linked above. Those pages establish releases and compatibility, while actual unauthenticated artifact resolution belongs in the integration harness.

## Exact recipe configuration

The three migration composites in the tuple table take no mandatory options. Their fully qualified IDs are present in the linked release-tagged YAML, rather than inferred from today's recipe catalog. The Boot composites select `3.5.x`/`4.0.x`, so pinning the recipe artifact alone does **not** pin the resulting Boot patch. An assertion should check the intended release line and actual resolved version, or the harness should use a controlled metadata snapshot.

For deterministic same-line Maven maintenance, define a local declarative recipe:

```yaml
type: specs.openrewrite.org/v1beta/recipe
name: integration.BootMaintenance
displayName: Upgrade Spring Boot maintenance release
recipeList:
  - org.openrewrite.maven.UpgradeParentVersion:
      groupId: org.springframework.boot
      artifactId: spring-boot-starter-parent
      newVersion: 3.4.13
```

`UpgradeParentVersion` requires `groupId`, `artifactId`, `newVersion`; optional `onlyExternal` defaults false. `UpgradePluginVersion` uses the same three required names and optional `versionPattern`, `trustParent`, and `addVersionIfMissing`. `trustParent` is relevant when checking plugins inherited from the Boot parent. A configurable Java-level recipe uses `org.openrewrite.java.migrate.UpgradeJavaVersion` with integer option **`version`**, not `newJavaVersion`. Required options must be supplied through a declarative wrapper recipe for ordinary plugin execution. The parent/plugin options are also used in the pinned Boot/Java YAML above. [Parent options](https://docs.openrewrite.org/recipes/maven/upgradeparentversion), [plugin options](https://docs.openrewrite.org/recipes/maven/upgradepluginversion), [Java options](https://docs.openrewrite.org/recipes/java/migrate/upgradejavaversion).

For the selected **Boot 3.5.15 → 3.5.16** fixture, use the same parent recipe with `newVersion: "3.5.16"`, leaving `java.version` unchanged. If the fixture imports `spring-boot-dependencies` rather than using the Boot parent, use the Maven dependency recipe instead:

```yaml
type: specs.openrewrite.org/v1beta/recipe
name: integration.Boot35Patch
displayName: Upgrade Spring Boot 3.5 patch
recipeList:
  - org.openrewrite.maven.UpgradeParentVersion:
      groupId: org.springframework.boot
      artifactId: spring-boot-starter-parent
      newVersion: "3.5.16"
  - org.openrewrite.maven.UpgradeDependencyVersion:
      groupId: org.springframework.boot
      artifactId: spring-boot-dependencies
      newVersion: "3.5.16"
      overrideManagedVersion: true
```

The second entry is only relevant to a declared BOM/dependency coordinate; it does not replace the parent recipe. `org.openrewrite.maven.UpgradeDependencyVersion` has required strings `groupId`, `artifactId`, `newVersion`; optional `versionPattern`, boolean `overrideManagedVersion` (default false), and list `retainVersions`. Exact `newVersion` values are supported; quote them in fixture YAML. For an ordinary direct dependency outside Boot management, target its exact artifact and normally leave `overrideManagedVersion` false. These options are verified against the [official Maven recipe documentation](https://docs.openrewrite.org/recipes/maven/upgradedependencyversion); the v8.89.0 source URLs could not be retrieved, so the harness should still validate recipe loading with plugin 6.46.1. Boot 3.5.15 exact Central pages/metadata also could not be retrieved through this browser; the official announcement supplies primary-source publication evidence, and actual POM resolution remains a build check.

## Minimal fixtures and meaningful assertions

These fixture designs are implementation recommendations, not claims from the documentation.

1. **Maven Java 8 → 25:** one real Java service, one Jupiter behavior test, POM with explicit release/source level 8 and compiler/Surefire plugins. A compression utility using `java.util.zip.Deflater.end()` gives the pinned Java 25 recipe a documented, type-aware transformation to `close()`. Assert Java level 25, that source transformation, successful compile/test on JDK 25, and nonzero test count. Retain JUnit 5 initially to avoid conflating language and testing-framework migrations. The selected source transformation is explicitly defined in the [3.42.1 YAML](https://raw.githubusercontent.com/openrewrite/rewrite-migrate-java/v3.42.1/src/main/resources/META-INF/rewrite/java-version-25.yml).
2. **Same-Java Boot maintenance:** a `@SpringBootApplication`, a pure service bean, and a small context/behavior test using `spring-boot-starter-test`. Keep `java.version=17` or `21`; start below 3.4.13, upgrade the parent, then verify the context starts and service behavior still passes. Verify dependency/plugin ownership through the effective POM and explicitly check the Java property stayed fixed.
3. **Boot 3.4 → 3.5:** reuse the small application and its test; exercise the official composite rather than a text-only parent edit. Verify migrated parent/BOM and managed dependencies plus real behavior. A property migration assertion should only be added after selecting a property present in the exact recipe artifact.
4. **Boot 3.5 → 4:** add one service mocked with `@MockBean` in a context test. The tagged Boot 4 composite includes `ReplaceMockBeanAndSpyBean`; Spring confirms removal of `@MockBean` and replacement with `@MockitoBean`. This gives a concrete migration beyond version changes without requiring a database, external service, or HTTP port. If a web fixture is used, account for the starter rename to `spring-boot-starter-webmvc` in the tagged composite. [Recipe source](https://raw.githubusercontent.com/openrewrite/rewrite-spring/v6.37.1/src/main/resources/META-INF/rewrite/spring-boot-40.yml), [Spring migration guidance](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide).
5. **Gradle catalog + locks:** duplicate the same tiny Java application as `build.gradle` and `build.gradle.kts` projects. Use the `java` plugin, JUnit API/engine/launcher dependencies, `useJUnitPlatform()`, and a real behavior test. Put JUnit's shared version under `[versions]` in `gradle/libs.versions.toml` and reference it from `[libraries]`. Use `libs` accessors in each DSL. Gradle auto-imports this conventional filename; importing it again explicitly is unnecessary. [Catalog documentation](https://docs.gradle.org/current/userguide/version_catalogs.html).

For locked Gradle fixtures, enable dependency locking and generate `gradle.lockfile` using a task that actually resolves configurations, with `--write-locks`. After the catalog upgrade, regenerate lock state and run the normal test build without `--write-locks`; assert the selected dependencies appear at the intended versions in the catalog and lock, and that a nonzero number of tests passed. The official guide documents `dependencies --write-locks` and states that only resolved configurations are written. Do not merely hand-edit a lockfile or count a successful dependency report as a successful behavior test. These fixture assertions follow from [Gradle locking semantics](https://docs.gradle.org/current/userguide/dependency_locking.html).

The Gradle 8.14/8.14.3 versioned catalog/locking URLs could not be retrieved through this research tool. The source for those sections is explicitly the current official Gradle manual, and exact 8.14.3 behavior still needs the real fixture run.

## Target JDK 25 source

Use Eclipse Adoptium's Temurin download service, selecting JDK 25 and the host OS/architecture, or pin a specific vendor release such as **Temurin 25.0.4+7** for repeatability. Adoptium links its REST API and Swagger from the vendor download page; its official GitHub release confirms that exact release and provides platform assets. Record the chosen archive URL and checksum at acquisition time; this research did not download or verify an archive. [Vendor downloads/API entry point](https://adoptium.net/temurin/releases/?version=25), [official pinned release](https://github.com/adoptium/temurin25-binaries/releases/tag/jdk-25.0.4%2B7).

The official release's expanded asset list verifies the Linux x64 HotSpot JDK archive, checksum companion, and published archive SHA-256:

- [Archive: OpenJDK25U-jdk_x64_linux_hotspot_25.0.4_7.tar.gz](https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4%2B7/OpenJDK25U-jdk_x64_linux_hotspot_25.0.4_7.tar.gz).
- [Checksum companion](https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4%2B7/OpenJDK25U-jdk_x64_linux_hotspot_25.0.4_7.tar.gz.sha256.txt).
- Archive SHA-256: `e58fcdcd637b25c03ca84cbbcefc70d11efb8f4b4cbd05decc9f661769d77f94`. This is the archive digest, not the separately displayed digest of the checksum text file. [Official expanded assets](https://github.com/adoptium/temurin25-binaries/releases/expanded_assets/jdk-25.0.4%2B7).

The asset names and archive digest are verified from the vendor listing. The checksum companion's redirect could not be fetched by the browsing tool, and no archive was downloaded. Linux aarch64 or Alpine hosts require their corresponding different assets.

## Actual Java 8 runtime baseline

The official Temurin 8 release page identifies **`jdk8u504-b01`** as the current latest release at verification time. Pin the release tag in the bootstrap rather than retaining a moving `latest` URL. The vendor's expanded asset listing confirms the Linux x64 HotSpot **JDK** archive and its published digest. [Official release](https://github.com/adoptium/temurin8-binaries/releases/tag/jdk8u504-b01), [official assets](https://github.com/adoptium/temurin8-binaries/releases/expanded_assets/jdk8u504-b01).

- [Archive: OpenJDK8U-jdk_x64_linux_hotspot_8u504b01.tar.gz](https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u504-b01/OpenJDK8U-jdk_x64_linux_hotspot_8u504b01.tar.gz).
- [Checksum companion](https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u504-b01/OpenJDK8U-jdk_x64_linux_hotspot_8u504b01.tar.gz.sha256.txt).
- Published archive SHA-256: `9c70e102f527ac674ac2fe9c7d47b9a04e2d19842ba5ab8e9b33f368bbadfaea`. The digest is associated with the archive entry in the vendor listing, not its JSON/checksum companions. [Source](https://github.com/adoptium/temurin8-binaries/releases/expanded_assets/jdk8u504-b01).

The top-level extracted directory is **not verified** by the release listing; `jdk8u504-b01` is a plausible naming inference rather than an inspected archive path. Inspect the downloaded archive's members to discover the root, or extract with one component stripped into an explicitly chosen JDK directory. This research did not download the archive. Verify `bin/java -version` and `bin/javac -version` after extraction before claiming that the baseline ran on Java 8.
