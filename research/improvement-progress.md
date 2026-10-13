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

## Step 3 — independent project policy

Added a strict project-policy schema/example and read-only validator. Live completion
requires a separately supplied policy file and its exact SHA-256 binding. The gate checks
module/component scope, selected versions/actions/owners, Java targets and preservation,
required check identities/outcomes, support, evidence age and snapshot exclusions.
Policy changes belong in reviewed project instructions/CI inputs; the hash alone is not
proof of reviewer identity. Examples do not establish organizational requirements.

Validation: 41 default tests pass, five integrations skip; policy and report examples,
skill metadata and whitespace checks pass. Adversarial cases remove required checks or
weaken support, age, scope, owner, versions, Java targets and input coverage; all reject.
Malformed/duplicate policy scope and missing builds reject. Matching policy/report passes.

## Step 4 — collected execution evidence

Added an explicit-command runner recording real exit codes/timeouts, input and policy
digests, tool-version probes, logs, fresh nonzero XML test counts, and resolved graphs.
Preserved XML/graph copies survive later clean builds. The live gate verifies execution
records against final inputs, artifact bytes, commands, XML counters and policy. Supplied
baseline counts require retained baseline execution evidence. No commands are read from
reports. Local records are consistency evidence, not signed tamper-proof attestations.

Validation: 46 default tests pass and six opt-in integrations skip. Real Maven 3.9.12
and Gradle 8.14.3 collection independently passes: one executed native test per fixture,
Maven dependency-plugin 3.11.0 JSON tree, Gradle native dependency output, and actual JVM/
build-tool probes. The retained-copy integration rerun passes in 12.909 seconds. Failure,
timeout, changed-input, stale/zero/failing XML, contradictory process/count/graph and
invented baseline-count cases reject. Skill metadata and whitespace checks pass.

## Step 5 — reproducible CI and real agent evaluations

Resolved and hash-locked every development dependency, retaining Python 3.10 support.
All four Linux/Windows and Python 3.10/3.14 wheel combinations resolve with enforced
hashes; 46 default tests pass in the exact locked local environment (six explicit
integration skips). The CI expansion adds five full migrations, native execution-evidence
tests, pinned/checksummed Maven/Gradle/JDK provisioning, and retained synthetic artifacts.

Installed Codex 0.162.1, Claude Code 2.1.270 and Copilot 1.0.88 each pass the same
corrected private-parent audit and exact same-Java maintenance edit. Independent builds
execute one test before/after, preserve Java 17 bytecode, pass packaged HTTP startup,
and confirm a no-op second agent request. Harness fixture/tool-allowlist errors found
during evaluation were corrected and affected cases rerun successfully.

The remote became available during this step. Step 5 was committed as `e9594dc` and
pushed to `validation/java-modernize-enterprise`. The expanded hosted workflow passed
all four platform/Python jobs and the full migration job on that exact commit. Downloaded
CI artifacts independently confirm all five stable migrations and both native evidence
collectors. [Run 38460355851](https://github.com/jeremybusk/modernize-java-skill/actions/runs/38460355851)
supplies the hosted result. All five requested improvement steps are implemented and
validated; detailed platform outcomes and bounded coverage are recorded in
[platform-validation.md](platform-validation.md).

## Step 6 — timestamped lifecycle documents and coordinated runs

Implemented in three validated increments: `4b516c6` introduces timestamped run storage,
JSON schema and rendered Markdown templates; `5361667` adds run-scoped process evidence,
immutable input checkpoints, dependency-aware invalidation and workspace completion gates;
the final increment integrates the workflow into the skill and improves source/review
links, standalone document metadata, diagnostics and native-build coverage.

Runs use explicit repository/application/workspace roots and portable relative mappings.
The UTC timestamp and slug appear in every lifecycle document filename and the manifest.
A JSON latest-run pointer avoids symlink requirements. Compact and expanded layouts render
shared facts from bound repository reports. Audits remain distinct from implementation;
each repository must pass its independent live gate for overall implementation completion.

Validation on 2026-10-13: 62 default tests pass, with six opt-in integration skips. The
selected native integration also passes against actual Maven and Gradle builds: one test
executes per project, both resolved graphs and tool probes are captured under run-scoped
paths, and checkpoint/resume plus generated-document consistency checks pass. Synthetic
two-repository process fixtures separately exercise all-repository live completion,
partial-repository rejection, changed inputs/policy, and downstream invalidation.

Skill metadata, local documentation links, archive checksums/reproducibility and whitespace
checks pass. The existing CI matrix discovers the added tests and the updated native
integration automatically. This increment was validated locally; no new hosted workflow
or authenticated agent evaluation was run. Earlier hosted/agent results above describe
their recorded commits, not this new document workflow. These checks establish document
and evidence consistency, not arbitrary application compatibility or deployment approval.
