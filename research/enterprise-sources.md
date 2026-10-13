# Enterprise modernization: verified implementation constraints

Primary-source review on 2026-10-12. These are tool and workflow constraints, not
claims that a particular application is production ready. Release numbers are
deliberately omitted; resolve compatible tool versions when executing a migration.

## Repository access and disconnected operation

- Maven repository mirrors select at most one mirror per repository, do not
  aggregate mirrors, and support `mirrorOf` matching. An internal repository
  manager must provide the needed combined view. A `mirrorOf=*` configuration
  requires that mirror to contain or proxy all required artifacts. Preserve the
  existing corporate mirror and authentication arrangement rather than adding a
  public fallback. The last sentence is our operational recommendation, derived
  from Maven's documented mirror behavior. [Maven mirror guide](https://maven.apache.org/guides/mini/guide-mirror-settings.html)
- Maven settings distinguish dependency repositories and plugin repositories,
  and contain server credentials and proxy settings. Inventory their existence
  and relevant policy without copying secrets into modernization reports.
  [Maven settings reference](https://maven.apache.org/settings.html)
- Maven `-o` requests offline behavior; the documentation says many plugins honor
  it. Consequently, do not claim it enforces an air gap for arbitrary plugins or
  processes. Use the environment's actual network controls when required and
  report missing cached dependencies or unavailable release evidence.
  [Maven repository and offline guide](https://maven.apache.org/guides/introduction/introduction-to-repositories.html)
- Gradle normal content filters restrict one repository's contents;
  `exclusiveContent` additionally keeps matching coordinates out of other
  repositories. Exclusive filtering in `pluginManagement` makes later project
  `buildscript.repositories` declarations illegal. Preserve working repository
  ownership, inspect dependency and plugin paths, and verify configuration before
  adding filters. [Gradle content filtering](https://docs.gradle.org/current/userguide/filtering_repository_content.html)

## Locked versions and artifact trust

- Gradle locking records resolved dependency versions and must be updated when
  planned dependency changes conflict with lock state. It does not make changing
  `-SNAPSHOT` coordinates immutable. `lockAllConfigurations()` does not include
  buildscript configurations; buildscript classpath locking requires separate
  configuration. Check which configurations are actually resolved, including
  subprojects and build logic, rather than asserting universal coverage.
  [Gradle dependency locking](https://docs.gradle.org/current/userguide/dependency_locking.html)
- Gradle dependency verification checks artifacts and, by default, metadata.
  Its generated baseline trusts whatever it downloads; generated checksums must
  be reviewed. Checksum equality establishes content identity to an expected
  value, not publisher trust by itself. Maintain strict verification and inspect
  unexpected changes instead of disabling verification or accepting arbitrary
  new hashes to make builds pass. Treat known intentional artifact changes as
  documented updates to the trust baseline. [Gradle dependency verification](https://docs.gradle.org/current/userguide/dependency_verification.html)

## Compatibility beyond successful compilation

- japicmp can enforce source or binary compatibility between old and new JARs.
  Classes extending or implementing external types need the appropriate old and
  new dependency classpaths. Missing-class suppression can remove evidence
  needed for analysis; do not present an incomplete analysis as a passing API
  gate. [japicmp CLI documentation](https://siom79.github.io/japicmp/CliTool.html)
- Revapi's Java extension analyzes class and method signatures; its documented
  checks distinguish source, binary, and potential semantic consequences. For
  example, an annotation default can change behavior while preserving source
  and binary compatibility. Our recommendation: retain contract, serialization,
  database, and integration tests alongside API comparisons; static signature
  checks cannot establish all runtime behavior. [Revapi Java overview](https://revapi.org/revapi-java/0.28.4/index.html),
  [Revapi documented differences](https://revapi.org/revapi-java/0.28.1/differences.html)

## Reproducible output and evidence integrity

- Maven documents reproducible archive timestamps and a two-build comparison
  using the artifact plugin. Configuring reproducible settings is preparation,
  not evidence of byte-for-byte reproducibility; run a controlled rebuild and
  comparison when that property is required. Plugin capability and environment
  differences still matter. Preserve the original baseline when comparing a
  second build; a second installation can overwrite it.
  [Maven reproducible builds guide](https://maven.apache.org/guides/mini/guide-reproducible-builds.html)
- SLSA artifact verification includes checking the signed envelope against
  trusted identities and matching the statement subject to the actual artifact
  digest, then evaluating provenance against expectations. A provenance file's
  presence alone supplies no verified guarantee. Our evidence-bundle
  recommendation: connect source revision, build inputs, final artifact/image
  digest, SBOM, scan time, and verification result; distinguish unavailable
  attestations from failed verification and do not claim a SLSA level merely
  because a file was generated. [SLSA artifact verification](https://slsa.dev/spec/v1.2/verifying-artifacts)

## Advisory freshness and bounded exceptions

- OSV records distinguish publication, modification, withdrawal, and aliases.
  Later modification time is authoritative for duplicate records of an ID;
  aliases describe the same vulnerability. A `last_affected` range boundary is
  not interchangeable with a known fixed version. Record retrieval time and
  advisory identity/status, deduplicate aliases, and preserve the difference
  between known fixed versions and incomplete range evidence.
  [OSV schema](https://ossf.github.io/osv-schema/)
- CycloneDX VEX expresses exploitability in a product context through analysis
  status, justification, and response. It does not turn an unsupported
  assumption into evidence of non-exploitability. Our workflow recommendation:
  use an owner, evidence, affected artifact/environment scope, and expiry for
  accepted exceptions; do not auto-create `not_affected` findings from a clean
  test suite or absence of a scanner result. [CycloneDX VEX use case](https://cyclonedx.org/use-cases/vulnerability-exploitability/)

## Release and rollback safety

- A Kubernetes canary runs stable and candidate versions concurrently; production
  rollouts commonly use controllers or CI/CD to manage monitoring, promotion,
  and rollback. Define project-specific health and performance thresholds and
  observation time before planning promotion. That threshold requirement is
  our recommendation, not a universal Kubernetes default.
  [Kubernetes canary deployment](https://kubernetes.io/docs/tutorials/stateless-application/canary-deployment/)
- AWS documents separating database schema and code changes so that schema-first
  changes work with old application code, or code-first changes work with the
  old schema. For shared databases, plan backward-compatible stages before
  treating application rollback as safe.
  [AWS schema-change guidance](https://docs.aws.amazon.com/whitepapers/latest/blue-green-deployments/best-practices-for-managing-data-synchronization-and-schema-changes.html)
- Mixed versions must agree on stored and wire formats. Amazon's rollback
  guidance describes preparing all readers before activating new writers,
  retaining old-format reading until backfill finishes, and testing partial
  deployment, full deployment, and rollback under traffic. Reverting a Git commit
  or image cannot itself restore incompatible persisted state. Our recommendation:
  name the last safe rollback version and explicitly identify irreversible
  schema, data, and protocol steps in the release handoff.
  [Amazon rollback-safety guidance](https://aws.amazon.com/builders-library/ensuring-rollback-safety-during-deployments/)

## Package validation and CI release snapshot

- `jsonschema.Draft202012Validator.check_schema()` validates the schema itself;
  validator construction assumes it is valid. Formats are informational unless
  a format checker is passed. `FormatChecker` accepts unknown formats, and
  missing optional format dependencies also allow validation to succeed.
  Explicitly ensure each required checker is present or provide a tested local
  checker before claiming timestamps/URIs were validated.
  [jsonschema validation documentation](https://python-jsonschema.readthedocs.io/en/stable/validate/)
- Local observation: pre-provisioned `jsonschema` 4.19.2 has `date` and `uuid`
  checkers but lacks `date-time` and `uri`; a validator with `FormatChecker()`
  accepted `not-time` under `format: date-time`. This observation applies to the
  current environment, not every installation of that release.
- On the review date, official stable release pages identify `actions/checkout`
  v7.0.1 and `actions/setup-python` v7.0.0. Their release commit links resolve to
  `3d3c42e5aac5ba805825da76410c181273ba90b1` and
  `5fda3b95a4ea91299a34e894583c3862153e4b97`, respectively. Both tagged
  `action.yml` files declare `node24`. These are CI packaging observations, not
  permanent latest-version defaults; recheck release and runner compatibility
  when updating them.
  [Checkout release](https://github.com/actions/checkout/releases/tag/v7.0.1),
  [Checkout commit](https://github.com/actions/checkout/commit/3d3c42e5aac5ba805825da76410c181273ba90b1),
  [Checkout action metadata](https://github.com/actions/checkout/blob/v7.0.1/action.yml),
  [Setup Python release](https://github.com/actions/setup-python/releases/tag/v7.0.0),
  [Setup Python commit](https://github.com/actions/setup-python/commit/5fda3b95a4ea91299a34e894583c3862153e4b97),
  [Setup Python action metadata](https://github.com/actions/setup-python/blob/v7.0.0/action.yml)
