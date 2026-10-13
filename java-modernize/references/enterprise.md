# Enterprise operation

Use this reference when the project has shared platforms, private repositories, multiple
consumers, restricted networks, or an enterprise-readiness request. Scale the work to
actual constraints. The following are engineering practices, not a compliance certification
or a new mandatory approval workflow.

## Establish the effective project policy

Read existing repository/organization instructions, support policy, approved JDK vendors,
Java floors, release-line constraints, supported OS/architectures, repository/image
allowlists, security/license rules, existing exceptions, CI commands and release procedure.
Record the source and scope of each material constraint. Use the user's explicit choices
and existing authorization; ask only for a missing constraint that changes the outcome.
Do not fabricate a risk owner, waiver, approval, ticket, or commercial support entitlement.

For the optional machine gate, establish a separate reviewed project policy before edits;
see [the report contract](enterprise-report.md). It defines scope and required checks
independently of the resulting report. Supply its trusted copy to CI and retain its digest.

An enterprise vendor's support statement may differ from upstream OSS support. Verify
the selected distribution and actual entitlement through available organizational evidence.
If access is missing, report support as unverified. Do not infer enterprise support from
a vendor logo, Maven artifact, or planned roadmap.

For a shared parent/BOM or internal Gradle plugin owned elsewhere, update the local
declared reference or prepare the owning change in scope. Do not shadow it with dozens
of local overrides or publish a replacement platform without authorization.

## Private artifact resolution and restricted execution

Inventory effective Maven mirrors, dependency **and plugin** repositories, extensions,
processor paths, Gradle settings/buildscript/pluginManagement repositories, toolchain
provisioning, recipe artifacts, wrapper distributions, image registries and public/private
namespace routing. An artifact existing upstream does not mean the mirror has approved it.

Use existing credentials and trusted configuration without printing values or copying
them into reports. Sanitize URLs, command arguments and diagnostic output. Inventory
does not require exporting settings files, environment dumps or a dependency list to a
public service. Check remote API/scanner disclosure rules before sending private coordinates.

Preserve mirror/content rules and artifact trust checks. Do not add `mavenCentral`,
`pluginPortal`, a new proxy, insecure repository, trust-all TLS, public fallback for private
coordinates, or arbitrary tool downloads just because resolution failed. Record the
repository/namespace/owner requiring action and continue independent offline work.

Maven/Gradle offline flags are build-resolution options, not network isolation. Plugins,
tests and scripts execute code and may contact services. Use the organization's actual
network boundary for a restricted run; avoid tasks that publish artifacts, apply database
migrations, or mutate infrastructure during build verification.

Sources: [Maven mirror settings](https://maven.apache.org/guides/mini/guide-mirror-settings.html),
[Maven offline CLI](https://maven.apache.org/ref/current/maven-embedder/cli.html),
[Gradle repository filters](https://docs.gradle.org/current/userguide/filtering_repository_content.html).

## Supply-chain evidence and security exceptions

Review lockfiles and dependency verification independently: locks constrain resolution,
checksums/signatures concern artifact bytes/trust. Gradle locks do not freeze changing
SNAPSHOT contents; ordinary `lockAllConfigurations` does not cover the buildscript
classpath. Inspect plugins, wrappers, processors, recipes, native binaries and image
digests as well as application dependencies. Bootstrapping checksums from downloaded
bytes does not independently establish those bytes are trustworthy.

For available tooling, generate the organization's required SBOM format from the resolved
packaged application and preserve the artifact digest/build identity connecting it to the
scan. Use CycloneDX/SPDX according to existing policy; do not claim an SBOM is a security
scan or that signatures alone prove absence of vulnerabilities. Record scanner/database
version and observation time, unavailable coverage, affected version ranges, and fix versions.

Prioritize according to the actual security policy and applicability, not CVSS alone.
Keep existing CVE-driven pins unless verified platform versions contain the fix. A false
positive or accepted risk needs the actual rationale, owner, tracking reference, expiry
and affected scope available from the organization. Do not create a suppression/VEX
statement or label an issue "not exploitable" merely because a test passes. Never turn
expired/unknown exceptions or unavailable advisory data into a clean security claim.

Sources: [Gradle locks](https://docs.gradle.org/current/userguide/dependency_locking.html),
[verification](https://docs.gradle.org/current/userguide/dependency_verification.html),
[CycloneDX](https://cyclonedx.org/specification/overview/),
[SPDX specifications](https://spdx.dev/specifications/).

## Shared libraries, platform upgrades and consumer contracts

Capture the released baseline API/artifact and representative supported consumers.
Where the repository already uses API checks, run them against the old/new artifacts
with the respective dependency classpaths. Revapi/japicmp can detect API/binary changes;
they cannot establish wire, storage, reflection, annotation, or behavioral compatibility.
Test the published minimum runtime and any supported native/OS profiles affected.

Include schema/serialization fixtures and representative consumers for changes to
Jackson, JAXB, Protobuf/gRPC, persistence, messaging or generated clients. Test old-reader/
new-writer and new-reader/old-writer combinations where the service contract requires it.
Distinguish an internal source refactor from a public API/ABI break, even if all local
modules compile together. Native images need separate reflection/resource/native/JNI
configuration and an actual supported native-build/runtime check when that target is used.

Sources: [Revapi](https://revapi.org/revapi-site/main/),
[japicmp](https://siom79.github.io/japicmp/).

## Batches, recovery and rollout boundaries

For substantial migrations, keep a compact plan/checkpoint using existing conventions:
baseline revision and dirty state; module/consumer scope; version owners and sources;
ordered dependency batches; required checks/environments; changed files/artifact hashes;
completed and pending work; unresolved constraints; temporary flags/overrides and removal
conditions. Redact credentials and private data before sharing it.

Before resuming, inspect current changes and ownership. If a user or another tool changed
the inputs, invalidate relevant results and recompute the plan rather than reapplying old
diffs or restoring the entire tree. An identical already-modernized input should result
in a documented no-op, not repeated recipes or unrelated formatting.

Recovery from local edits must preserve pre-existing work. Describe or revert only the
agent-owned changes when authorized; do not use destructive resets or publish checkpoint
commits automatically. Successful package validation is separate from production readiness.

When release planning/deployment is requested, define the actual rollout environment,
observed service metrics/SLOs, smoke/contract checks, canary scope, abort criteria and
known-good artifact/configuration. A rollback must account for stored data, database
schema, migrations, broker/wire contracts, and mixed versions. Prefer compatible staged
schema changes when applicable. Do not promise rollback by redeploying an old binary
after an irreversible schema or data change. Execution still follows existing deployment
authorization; local modernization does not itself deploy the result.

Source: [Amazon Builders' Library: rollback safety](https://aws.amazon.com/builders-library/ensuring-rollback-safety-during-deployments/).
