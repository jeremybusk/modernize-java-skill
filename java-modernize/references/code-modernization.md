# Code modernization at the existing or upgraded target

Use Java Evolved's before/after approach, but verify contracts and final API availability
against the actual compiler/API target. Search matches are candidates, not proof of an
outdated pattern. Keep readability and project conventions ahead of feature count.

## Final-feature guide

These are introduction releases for selected **final** features, not recommendations
to raise the target. A newer build JVM does not make them available under an older
`--release`. For later releases or APIs, verify the target Javadoc/JEP status directly.

| Final since | Selected idioms / APIs |
| --- | --- |
| 8 | Lambdas, streams, `java.time`, `CompletableFuture` |
| 9 | Collection factories, `Optional.or`/`ifPresentOrElse`, `Stream.ofNullable`/`takeWhile`, private interface methods |
| 10 | Local `var`, collection `copyOf`, unmodifiable collectors |
| 11 | `String.isBlank`/`strip`/`lines`/`repeat`, `Files.readString`/`writeString`, `Path.of`, HTTP client |
| 14 / 15 | Switch expressions / text blocks and `String.formatted` |
| 16 / 17 | Records, `instanceof` patterns, `Stream.toList`, `mapMulti` / sealed types, `HexFormat`, `RandomGenerator` |
| 21 | Virtual threads, pattern switch, record patterns, sequenced collections |
| 22 / 23 | Unnamed variables/patterns, FFM API / Markdown Javadoc comments |
| 24 / 25 | Stream gatherers, Class-File API / scoped values, flexible constructor bodies, module imports, compact source files and instance main methods |

On **Java 25**, structured concurrency, stable values, and PEM encoding APIs remain
preview. Primitive patterns are also preview language features. They are not defaults
for production modernization. Do not use old `StructuredTaskScope.ShutdownOnFailure`
examples as Java 25 code: its preview API changed. Preview binaries/configuration are
release-specific; if requested, verify compiler, tests, runtime, deployment and tools
for that exact release. Incubator modules are a different status and configuration.
String Templates previews from 21/22 were withdrawn; do not recommend them as a stable
modernization path. Re-check all feature status for any target later than 25.

Sources: [JDK 25 language changes](https://docs.oracle.com/en/java/javase/25/language/java-language-changes-summary.html),
[JDK 25 preview APIs](https://docs.oracle.com/en/java/javase/25/docs/api/preview-list.html),
[JDK 25 StructuredTaskScope](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/StructuredTaskScope.html),
[JDK 25 release notes](https://www.oracle.com/java/technologies/javase/25-relnote-issues.html).

## Preserve the contracts that examples often overlook

| Candidate | Check before replacement |
| --- | --- |
| `List.of` / `Set.of` / `Map.of` | Unmodifiable structure, null rejection, duplicate rejection for factory arguments to sets/maps, iteration order and identity assumptions |
| `copyOf` | Snapshot vs backed view; shallow copying and null handling; not a deep immutable copy |
| `Stream.toList()` | Unmodifiable result; later mutation and concrete-type assumptions; do not equate its null handling with collection factories |
| Record conversion | Changed accessor/API names, shallow immutability, equality, serialization shape, constructor requirements, framework proxies and persistence |
| `trim` → `strip` / `isBlank` | Different whitespace definitions; Unicode handling changes behavior |
| Text blocks | Indentation, escapes, trailing newline/whitespace and wire/query content |
| `java.time` | Zone/locale, DST, precision, parser strictness, storage/wire format and boundaries with legacy APIs |
| HTTP client replacement | Authentication, cookies, redirects, proxies, timeout/retry policy, reuse and resource ownership |
| Streams/lambdas | Side effects, encounter order, laziness, exception propagation, allocation and readability |
| Resource cleanup | Ownership, close timing, exception suppression; Cleaner is not an equivalent deterministic close |
| Sealed classes / exhaustive switch | Public extension contracts, frameworks/proxies, null handling and binary evolution |

Sources: [collection contracts](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/List.html),
[stream contracts](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Stream.html),
[records](https://docs.oracle.com/en/java/javase/25/language/records.html),
[String APIs](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/String.html).

Example: if callers mutate the result, preserve a mutable list explicitly:

```diff
- List<Item> items = stream.collect(Collectors.toList());
+ List<Item> items = stream.collect(Collectors.toCollection(ArrayList::new));
```

If an unmodifiable result is the intended contract and Java ≥16 is the API target,
`stream.toList()` is a suitable candidate. Inspect callers before choosing.
Do not automatically convert JPA entities to records; framework support for record
DTOs or embeddables does not establish support for record entities.

## Concurrency and performance

Virtual threads are final in 21 and fit blocking I/O workloads. They do not make
CPU-bound work faster or remove database/remote-service capacity constraints. Do not
pool virtual threads; bound scarce downstream resources, preserve cancellation/timeouts,
and check thread-local/context/observability behavior.

Monitor-related pinning with `synchronized` was addressed in JDK 24. On 24+, do not
rewrite locks solely for that former limitation. Native/foreign calls can still pin.
On 21–23, investigate actual hot blocking monitor paths before changing locking.
Measure representative workloads before changing collectors, executors, parallel streams,
or enabling AOT features. Scoped values model bounded immutable context; they are not
a universal replacement for mutable `ThreadLocal` state.

Source: [virtual thread guide](https://docs.oracle.com/en/java/javase/25/core/virtual-threads.html).

## Architecture migrations are separate decisions

EJB→CDI, JDBC→ORM/jOOQ, SOAP→REST, servlet→JAX-RS, JMS→reactive messaging, or
Spring XML→annotations can change transactions, security, lifecycle, delivery guarantees,
schema, or public contracts. Adopt them when the requested outcome and compatibility
allow it, not as an automatic consequence of raising Java or Jakarta versions.
Preserve existing frameworks unless replacement is in scope.

For each applied pattern, explain the reason, relevant Java/framework floor, files changed,
and contract checks. Prefer small groups of demonstrated improvements over a blanket
rewrite of every pattern from a catalog.
