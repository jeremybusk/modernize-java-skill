# Enterprise Java library maintenance audit

Audit completed within the permitted offline scope at 2026-10-13T02:09:44Z. No project files were changed. Maintenance candidates remain unverified; this is not an evidence-backed claim that the library is current, secure or ready to release.

## Scope and support promise

The four supplied files are raw inputs, not a complete resolvable build. Current `POLICY.md` governs. Production/minimum-consumer and test runtime floors remain **Java 11**; `pom.xml` declares `maven.compiler.release=11`. Build and compiler JVMs may be Java 21. Actual build/compiler/test JVMs, distributions and patch levels are unknown. A permitted Java 21 compiler does not change the API/bytecode target or authorize raising the test-runtime promise. No settings changed before/after this audit.

Only dependency patches within existing minor lines and artifacts approved through the corporate mirror are eligible. No network, builds, installations, publishing or deployment were attempted. No evidence age limit, approved vendor support entitlement or separate mandatory supported-release rule was provided; the earlier report's seven-day value is not inherited.

## Interrupted audit: what can resume

The earlier POM SHA-256 was `80c16dc20522389a6905226778e706fe8b2bf2f130ddb8a23c78a7a61a5c0ce2`; current POM SHA-256 is `cd336fdddafb73e6548d28090374deed0c1053dfc3d1d77e0e1ef3b4b07c7653`. The supplied validator rejects the old checkpoint's artifact hash. The old report's Java 17 source/constraints also conflict with current policy and with its own Java 11 module fields. It contained no resolved versions, selected candidates, dated primary sources or passing checks to reuse. Its statement that no organizational policy existed is obsolete now that `POLICY.md` is supplied.

Resume the reporting structure and unresolved-work list only after rebuilding scope from current inputs. Do not replay edits, restore an earlier tree or carry forward old compatibility/freshness conclusions. The old report's timestamp alone establishes no source freshness. Record fresh hashes for POM, settings, policy and prior report; this companion does so. No Git revision/dirty-state evidence is available; the companion records both as `null`.

## Declared owners and maintenance proposals

All resolved versions are unknown because the corporate parent and effective graph are unavailable. Latest available, latest compatible and selected candidates are all unknown. There are no numeric update recommendations.

| Component / local owner | Declared → resolved | Candidate / action | Constraint and missing evidence |
| --- | --- | --- | --- |
| Corporate parent / `pom.xml` | `com.example.internal:corporate-parent:7.1.0` → unknown | Unverified; defer | Parent supplies unknown inherited management; obtain actual bytes/model and verify any resulting dependency changes satisfy patch-only lines. Change the owning platform reference rather than adding child overrides. |
| JUnit Jupiter / `pom.xml`, `junit.version` | `5.14.4`, test scope → unknown | Unverified `5.14.x` patch only; defer | Verify actual publication, Java 11 test-runtime compatibility, runner/engine alignment, support and mirror availability. Do not infer publication from a declaration. JUnit 6 leaves the allowed dependency line and is not proposed. |
| Log4j Core managed security override / `pom.xml` | `2.24.3` → unknown | Retain declared pin; candidate selection deferred | A dependencyManagement entry does not prove actual runtime usage. Obtain advisory, actual governing ticket, resolved parent and packaged graph. No removal, waiver or clean-security claim is justified. Any eligible future dependency patch stays within `2.24.x` and preserves the security constraint. |
| Maven/plugins/processors/test runners / parent reference in `pom.xml` | Inherited/unknown → unknown | Unverified; defer | Inspect actual parent-owned compiler/Surefire/Failsafe and any present processors/agents/bytecode tooling. Their presence and versions cannot be invented from fixture omissions. |
| Runtime/test JDK patches / `POLICY.md` | Java 11 floor; patch/vendor unknown | Unverified; defer | Establish actual approved distribution and support entitlement; preserve minimum-runtime tests. |
| Build/compiler JDK / `POLICY.md` | Java 21 permitted; actual JVM unknown | Unverified; defer | Confirm approved toolchain, `--release 11` enforcement and independent Java 11 tests. Permission does not establish installation or require an upgrade. |

The supplied `settings.xml` has one corporate mirror with `mirrorOf=*`. This is declared routing, not evidence that settings are used by the actual invocation, artifacts are approved/available, credentials work or every toolchain/image/download path is governed. No public fallback or trust/credential modification is allowed. Assess dependency **and plugin/processor** availability internally when evidence is supplied. No upstream URLs were fetched or private coordinates sent externally.

## Validation and evidence

- Static inventory: read-only helper completed; recognized `pom.xml` and `settings.xml`, no truncated discovery or skips. Manual inspection included policy and old report. It resolved no versions.
- Old JSON/hash validation: **failed** because the POM hash changed. This is an invalid checkpoint, not a failing project build.
- Effective model/graphs, baseline build, Java 11 unit tests, security review and approved candidate availability: **not run** under the supplied policy. There is no test count evidence.
- API/consumer and integration checks: **not run**; real-project applicability, baselines and commands are absent. Fixture omissions do not establish that the project lacks these checks.
- JSON companion structure/consistency and input hashes: **passed**, helper exit 0 with `valid=true`, `implementation_complete=false`, `artifact_hashes_checked=true`. The optional `--require-complete` implementation gate returned exit 1 as expected for an audit. Passing report validation cannot prove compatibility, freshness or release readiness.

No build command was established from these fixtures. Once execution is permitted on the actual project, use its existing wrapper, approved settings/profiles and toolchains; obtain effective POM plus runtime/test/plugin/processor graphs before selecting changes. Execute its existing build/verify command with release 11, run unit tests on Java 11 and compare executed/discovered/skipped counts, validate representative minimum-runtime consumers and existing API/contract/security checks. A newer build JVM must remain separate from these runtime promises. Do not run those future checks on this raw fixture.

## Concrete remaining work

1. Obtain actual checkout identity/pre-existing changes, parent/effective models, wrappers/toolchains, dependency/plugin/processor graphs and released consumer baseline through permitted internal channels.
2. Establish compatible stable patch candidates within each existing dependency minor line with separate dated publication, Java 11 compatibility, approved mirror availability and support evidence. Identify any present CI/image/processor/agent paths in the full project rather than assuming them absent.
3. Resolve the actual Log4j advisory and owning ticket. Keep the existing override until the parent fix and removal condition are demonstrated; no exception was supplied.
4. When actual-project execution is authorized, apply no change until its tuple is verified; use existing validation commands and retain Java 11 minimum-runtime evidence. Re-inventory current inputs and invalidate checks if the parent, graph or owner files change.

The offline audit deliverables are complete. Candidate selection and implementation remain deferred; the report is not a maintenance no-op finding.
