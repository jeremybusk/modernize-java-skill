# JDK migration

Use this map to choose investigations; confirm the exact target's migration guide and
release notes. Changes are cumulative across all crossed feature releases, including
non-LTS releases. Do not impose every intermediate JDK as a mandatory build/deployment.

## Release boundaries

| Crossing | Investigate when applicable |
| --- | --- |
| 8 → 11 | JPMS/encapsulation, removed Java EE/CORBA modules, JAXB/JAX-WS dependencies and code generation, removed tools/flags, version parsing, G1 default, locale provider changes |
| 11 → 17 | Strong encapsulation, reflection/agents, removal of CMS and Nashorn, TLS/security changes, records/sealed/pattern identifiers and framework support |
| 17 → 21 | UTF-8 default since 18, CLDR/time-zone changes, finalization deprecated for removal since 18, dynamic-agent loading warnings in 21, virtual threads and runtime/GC behavior |
| 21 → 25 | Security Manager disabled in 24, Unsafe memory-access warnings in 24 and target-specific policy, native-access restrictions, JDK 23 processor defaults, monitor pinning fix in 24, ZGC changes, optional AOT tooling |
| Beyond these / non-LTS | Read every intervening release's official migration/release notes and feature status; do not infer coverage from the nearest LTS guide alone |

Read [Oracle migration preparation](https://docs.oracle.com/en/java/javase/25/migrate/preparing-migration.html)
and the actual target's guide. Vendor packaging, support, and JDK patches have their
own requirements. Match tools and options to the installed target JDK.

## Bytecode analysis: what gets scanned

Compile or obtain the relevant project outputs. Supply classpaths/module paths derived
from the resolved build. Example templates for a target JDK that supports these options:

```sh
<target-jdk>/bin/jdeps --jdk-internals --multi-release <target> --class-path '<resolved-classpath>' <project-output>
<target-jdk>/bin/jdeps --jdk-internals --multi-release <target> --class-path '<resolved-classpath>' <dependency-jar>
<target-jdk>/bin/jdeprscan --release <target> --class-path '<resolved-classpath>' <project-output>
<target-jdk>/bin/jdeprscan --release <target> --for-removal --class-path '<resolved-classpath>' <dependency-jar>
```

Replace placeholders, quote actual paths correctly for the shell, and repeat for the
appropriate artifacts. Putting JARs on the classpath does **not** guarantee every JAR
is an analysis input. For `jdeps`, use explicit inputs or documented recursive traversal
when needed and confirm output coverage. Do not hide unresolved classes with
`--ignore-missing-deps` and call the resulting report clean. `jdeprscan` finds uses of
deprecated JDK APIs, not every deprecated third-party API. Neither finds all reflection,
configuration/service loading, JNI/FFM, or generated runtime code.

Sources: [jdeps](https://docs.oracle.com/en/java/javase/25/docs/specs/man/jdeps.html),
[jdeprscan](https://docs.oracle.com/en/java/javase/25/docs/specs/man/jdeprscan.html).

## Runtime and behavior checks

- **Encapsulation:** upgrade the owning library before keeping `--add-opens`/
  `--add-exports`; if needed temporarily, document the exact package, owner, reason,
  and removal condition. Do not assume every class-loading failure is a bytecode
  library problem: verify classpaths, packaging, removed modules, and source errors.
- **Encoding:** UTF-8 became the default charset in JDK 18. Preserve actual file/wire
  contracts instead of mechanically making all I/O UTF-8. Console/native encoding
  and explicit legacy charsets require separate checks.
- **Locales/time zones:** test representative parsing/formatting and persisted data;
  locale providers/CLDR/tzdata change between feature and patch releases. Specify
  locale/zone for machine protocols instead of assuming workstation defaults.
- **Serialization:** validate JSON/XML schemas, object persistence, proxies, record
  accessors, serialVersionUID and cross-version readers/writers where relevant.
- **Resources:** finalization was deprecated for removal in 18 and remains present
  in 25. Prefer explicit ownership and `AutoCloseable`; Cleaner is a fallback for
  appropriate resources, not deterministic cleanup.
- **Agents/native/security:** exercise Mockito/profilers/APM and native libraries.
  Verify supported startup agent/native-access configuration; do not add blanket
  access flags, disable certificate checks, or re-enable obsolete algorithms.
- **Performance/GC:** inspect actual removed flags and defaults. Do not use
  `IgnoreUnrecognizedVMOptions` to conceal migration failures, select a new collector,
  or promise performance improvements without workload evidence. Rebaseline existing
  tuning against the intended image/resource limits.

Sources: [UTF-8 JEP](https://openjdk.org/jeps/400),
[JDK 25 deprecated APIs](https://docs.oracle.com/en/java/javase/25/docs/api/deprecated-list.html),
[JDK 24 release notes](https://www.oracle.com/java/technologies/javase/24-relnote-issues.html),
[JDK 25 release notes](https://www.oracle.com/java/technologies/javase/25-relnote-issues.html).
