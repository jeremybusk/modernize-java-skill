---
name: java-modernize
description: Modernize existing Java projects by upgrading the JDK, maintaining dependencies and tooling while Java stays fixed, migrating frameworks, or replacing outdated Java idioms. Use for Java modernization and ecosystem freshness audits, including Maven, Gradle, Spring, Jakarta, tests, CI, and containers. Do not use for unrelated feature development or general Java questions.
license: Apache-2.0
---

# Java Modernize

Deliver a working, reviewable modernization using versions verified at execution time.
Keep the user's Java target, compatibility promises, and chosen frameworks explicit.
All paths below are relative to this skill directory. No particular agent, MCP server,
commercial migration service, or bundled JDK is required.

For enterprise projects, private repositories, shared platforms, or an explicit enterprise
readiness request, read [enterprise operation](references/enterprise.md). Apply the
organization's existing constraints; do not invent an approval process or compliance claim.

## 1. Establish scope and baseline

Select the mode from the request; combine modes when appropriate:

| Mode | Outcome |
| --- | --- |
| Audit | Inventory, verified candidates, blockers, and a plan; no project edits. |
| Upgrade Java | Change the requested JDK/runtime and, when requested, the compilation target; update the ecosystem needed to support them. |
| Maintain current Java | Keep Java feature/release targets fixed; refresh supported JDK patches, dependencies, frameworks, plugins, wrappers, tests, CI, and images within compatibility constraints. |
| Modernize code | Apply suitable final APIs and idioms available at each module's compilation target, including when Java stays fixed. |

For an unspecified modernization request, preserve the current Java target and choose
compatible stable maintenance updates. Recommend major framework/JDK migrations
separately unless broad upgrades are already requested. A named target takes precedence;
do not silently replace a non-LTS target or enable preview features.

If a Java upgrade is explicitly requested without a target, choose a currently released,
vendor-supported LTS that the project's ecosystem supports and explain the selection.
Do not infer a future release is available merely from the current date.

Read repository instructions and inspect existing work before editing. Record baseline
build/test failures and use the project's wrappers and existing validation commands.
Do not stop at a proposal when implementation is requested and authorized.

Record the starting revision and pre-existing changes, affected modules/consumers,
available toolchains, permitted network/repositories, and actual required checks. For
substantial work, capture a plan with version owners, dependent batches, validation,
and rollback boundaries using the repository's conventions. Reuse existing authorization.

Read [inventory and build guidance](references/inventory-and-build.md). Optionally run:

```sh
python3 <skill-directory>/scripts/inventory.py <project-root>
```

The helper only lists static configuration evidence; it does not resolve effective
versions, execute builds, or check online releases. Inspect inherited parents, BOMs,
profiles, catalogs, convention plugins, included builds, and source sets yourself.
Distinguish **build JVM**, **compiler/toolchain JDK**, **compilation/API target**,
**test JVM**, and **deployment runtime**, per module. The installed JDK proves none
of the other settings. Preserve a published library's minimum supported Java version.

Resolve missing information from the repository first. Ask only for a consequential
constraint that cannot be inferred; continue independent work while it is unresolved.

## 2. Verify current candidates and their owners

Always read [version selection and freshness](references/version-selection.md).
For each applicable component, identify its declared and resolved version, the file or
upstream parent/platform that owns it, and a verified compatible candidate. Use current
upstream release notes, requirements, support policies, advisories, and artifact metadata.
An update-list command discovers candidates; it does not establish compatibility.

Audit the ecosystem even when source and target Java are equal. Include JDK patch and
vendor support, frameworks/BOMs, build tools/plugins, test engines, annotation processors,
bytecode/coverage/agents, common application libraries, JDBC/messaging clients, CI actions,
and runtime/build images where present. Only inspect technologies the project uses.
Read [ecosystem guidance](references/ecosystem.md) for applicable families.

Prefer supported stable releases within the requested scope. Separate the **latest
available**, **latest compatible**, and **selected** versions; document why they differ.
Resolve requirements across the whole tuple before editing. Update a managing BOM or
platform rather than independently overriding every managed dependency. Pin concrete
versions; never write `LATEST`, `+`, or an unverified version from memory.

Keep a compact evidence table in the modernization report:

| Component / owner | Current declared → resolved | Selected candidate | Constraints / reason | Primary source + checked date |
| --- | --- | --- | --- | --- |

When network or private metadata is unavailable, label candidates **unverified** and
record what remains to check. Do not claim that cached knowledge establishes freshness.

Separate public upstream publication from availability through the approved artifact
mirror. Check dependency, plugin, processor, toolchain, and image supply paths. A mirror
failure does not authorize public fallback or changing credentials/trust configuration.

## 3. Plan compatible, testable batches

Prioritize observed security issues, unsupported components, build/runtime blockers,
behavior changes, then optional idiom improvements. Deprecation alone is not a blocker.
Choose coherent batches such as wrapper/plugins, platform/framework, tests/coverage,
application libraries, deployment configuration, and source refactors.

For JDK changes, read [JDK migration](references/jdk-migration.md), including every
crossed release boundary. Where supported, first test on the target runtime/toolchain
while keeping the old compilation target, then raise that target if in scope. This
isolates some failures; it is not proof that every first-stage failure is a runtime issue.
If the compiler cannot emit the old target, use a supported intermediate toolchain or
document why the split is unavailable. Intermediate validation need not become a deployed
or committed intermediate release.

For source changes, read [code modernization](references/code-modernization.md).
Separate behavior-preserving edits from API, persistence, concurrency, or architecture
changes. Do not treat records, virtual threads, Jakarta, or an ORM as universal upgrades.

For shared libraries/platforms, identify downstream consumers and check API/binary,
wire, and persisted-data compatibility. Where deployment is in scope, plan mixed-version
operation and schema compatibility before claiming rollback is possible.

## 4. Apply changes at the source of truth

Update version-owning files and affected configuration, imports, APIs, CI, images,
documentation, lockfiles, and verification metadata together. Preserve independently
chosen build/test/runtime JDKs when their compatibility is intentional. Avoid unrelated
formatting or unrequested technology replacement. Review the resolved graph after edits.

For repeatable mechanical migrations, read [automation](references/automation.md).
Use verified, pinned recipes/tools with a dry run where available. Inspect their diff,
including semantic changes and unexpected files. Manual edits are a valid fallback.
Do not assume all OpenRewrite recipe binaries or hosted services are free or accessible.

Do not skip assertions, disable tests, weaken security, or hide obsolete JVM options
to make the migration pass. Preserve the user's work; stop retrying a failing approach
when new evidence requires a different plan. Deployment, publishing, infrastructure
replacement, and recurring automation require scope/authorization beyond local edits.

Before resuming an interrupted batch, compare the current revision/configuration and
resolved graph with recorded evidence; invalidate stale checks and candidates after
changes. Do not reset, stash, commit, or publish existing work merely to create a checkpoint.

## 5. Validate the resulting application

Read [validation and reporting](references/validation.md). Run the existing build,
unit and applicable integration tests using the intended toolchains. Verify test discovery
and counts after engine/plugin migrations, packaging, startup, and changed contracts.
For libraries, test the minimum promised runtime as well as any newer runtime in scope.
Investigate failures relative to baseline; do not present unrun checks as passing.

Use target-JDK bytecode tools when relevant; scan project output and dependency JARs
explicitly. They complement compilation and runtime tests and cannot prove reflection,
service loading, native integration, or framework compatibility.

## 6. Report completion and remaining work

Summarize what changed and why, Java targets before/after (including unchanged targets),
selected versions with evidence, commands and outcomes, behavior risks, and blockers.
Mark checks **passed**, **failed**, **not run**, or **not applicable**. Distinguish
implemented changes from recommendations and unsupported claims from verified facts.
For audits, provide prioritized concrete changes instead of implying implementation.

For enterprise work, produce a reviewable report and its JSON companion using
[the report contract](references/enterprise-report.md), unless an existing organizational
format already provides equivalent evidence. Validate the companion with the optional
helper or the organization's JSON Schema tooling. The helper checks structure, consistency,
and optionally artifact hashes; it cannot certify compatibility or deployment readiness.

For repeated maintenance, re-inventory and re-check live sources on each invocation.
If everything within scope is already current and compatible, report an evidence-backed
no-op. Suggest Renovate or Dependabot when useful; configure them only when requested
or included in the user's task. This skill does not update projects in the background.
