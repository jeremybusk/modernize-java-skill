# Modernization skill improvement sequence

The user requested all five improvements, with a validated, formatted commit per step.
Work proceeds in this order:

1. Complete Maven/Gradle migration scenarios: baseline, migration, tests/startup, rerun.
2. Completion gates tied to validation-time freshness and complete declared input snapshots.
3. Independent, validated project policy supplying required checks and upgrade constraints.
4. Automatic evidence collection from real command outcomes and build/test artifacts.
5. Hosted CI and real Codex/Claude/Copilot scenarios; hash-locked development dependencies.

The previously uncommitted enterprise enhancement is validated and committed first as
the baseline. Each step records its changes and executed verification before its commit.
Unavailable external execution is recorded as pending rather than reported as passing.

## Baseline

The existing 33-test suite and skill frontmatter validation pass. Enterprise guidance,
JSON report validation, expanded inventory, Java fixtures, packaging and CI configuration
are ready to commit. The earlier hosted CI and production-migration limitations remain
explicit in enterprise-validation.md.

## Execution requirements

- Synthetic integration projects and downloaded/cached toolchains stay under writable
  temporary directories; no production systems or user applications are modified.
- Current checkout initially has no Git remote. Hosted execution needs the intended
  GitHub repository, requested from the user while local work continues.
- Each committed step must pass relevant local validation. Integration results identify
  actual JDKs, build tools, recipes and dependency versions rather than assumed support.

## Step 1 — complete migration scenarios

Passed all five opt-in integration tests (121.428 seconds): actual Java 8 to 25
two-module Maven migration, Spring Boot maintenance and major upgrades, and Gradle
Groovy/Kotlin catalog updates with native lock regeneration. Each scenario builds,
executes tests, starts the application before/after, checks bytecode targets and
requires a no-op migration rerun. Gradle scenarios use manual catalog edits; they
do not claim coverage of the Gradle OpenRewrite plugin.

Executed with Maven 3.9.12, Gradle 8.14.3, Java 8u504, Java 21.0.12.1 and Java
25.0.4+7. Recipe artifacts and fixture versions are pinned historical test inputs,
not recommendations for the latest version. The Java migration demonstrated that
fresh attribution can enable another transformation; bounded stabilization and a
final independent rerun now catch that behavior.

The default suite passes 33 tests and skips the five explicitly selected network/
toolchain integrations. Skill metadata validation and whitespace checks also pass.

## Step 2 — live completion gate and input snapshots

The release gate now measures evidence age against validation time, rejects future
reports, and requires a bounded age plus a complete local input snapshot. It checks
the exact input set/hashes and requires graph artifact references for each module.
Ordinary validation still checks historical reports against their recorded timestamp.
Snapshot enumeration fails on unreadable files, symlinks and coverage bounds; wrapper
JARs and all non-generated project files are included. The exclusions are documented.

Validation: 37 default tests pass, five full-build tests skip; added live stale/future,
added/changed/deleted input, graph coverage and symlink/wrapper cases. Example report,
skill metadata and whitespace checks pass. Actual execution provenance is addressed
in step 4; supplied graph/log references do not yet prove a command was executed.
