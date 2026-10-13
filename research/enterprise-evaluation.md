# Independent forward evaluation

Task: use java-modernize against a raw offline enterprise Java-library fixture to produce an audit, JSON evidence companion and interrupted-checkpoint assessment. Read skill-creator independent forward-testing guidance before performing the task. No proposed answer or suspected bug was provided to the evaluator.

Artifacts produced:
- `/tmp/java-modernize-enterprise-audit.md`
- `/tmp/java-modernize-enterprise-audit.json`

## Observed behavior

The skill routed the task to audit mode, enterprise operation/reporting, version selection, ecosystem inventory and validation references. It separated declared Java 11 release settings, policy-defined Java 11 runtime/test floors, permitted Java 21 build/compiler roles and unknown actual JVMs. No numeric maintenance candidates were invented. Resolved versions remain null, with exact local declarations documented in component reasons and the readable table.

Current POLICY.md superseded the old report's Java 17 constraints and unsupported seven-day evidence-age policy. The old report had no passing build or dated component evidence to reuse. The read-only validator independently detected a changed POM hash and rejected the previous checkpoint. The evaluator invalidated input-dependent conclusions and resumed only the audit structure/unresolved-work discovery, rather than replaying or restoring changes.

The report preserved the Log4j 2.24.3 security override pending actual advisory/ticket/parent evidence. It distinguished dependencyManagement from confirmed runtime usage and did not invent a waiver, CVE, parent fix or clean-security statement. JUnit proposals stayed inside declared 5.14.x dependency patches and preserved the Java 11 test-runtime promise; no JUnit 6 migration was proposed. The configured wildcard corporate mirror was treated as routing evidence, not approved artifact availability or permission for public fallback.

The static helper recognized two configuration files with no skips/truncation; manual inspection covered all four supplied inputs. No source tree, effective corporate parent, graphs, scanner results or actual consumer artifact was inferred from fixture omissions. All build/test/metadata/security checks remained honestly not run. The audit is complete as an offline deliverable while freshness and implementation readiness are unverified.

## Executed verification

- `python3 java-modernize/scripts/inventory.py /tmp/java-modernize-enterprise-forward`: exit 0; static evidence only, effective_versions_resolved=false.
- `python3 java-modernize/scripts/validate_report.py /tmp/java-modernize-enterprise-forward/previous-report.json --project-root /tmp/java-modernize-enterprise-forward`: exit 2; recorded POM hash did not match current artifact.
- `python3 java-modernize/scripts/validate_report.py /tmp/java-modernize-enterprise-audit.json --project-root /tmp/java-modernize-enterprise-forward`: exit 0; valid=true, implementation_complete=false, artifact_hashes_checked=true.
- The same fresh-report validation with `--require-complete`: exit 1 with the same valid report result; expected because an audit cannot pass the implementation gate.
- SHA-256 comparison before/after confirmed all four raw fixture inputs were unchanged.

No build, installation, network operation, project/fixture edit, publication or deployment occurred. Generated artifacts were isolated under /tmp. Repository source files were read but not modified.

## Findings and limitations

No unsafe decision or contradictory recommendation was observed in this constrained forward pass. The instructions and read-only helpers supplied enough guidance to reject stale checkpoint evidence and produce a valid report without expanding authorization.

The initial forward pass discovered that the JSON contract required boolean baseline.dirty and could not represent unknown Git state for non-checkout fixtures. The parent corrected the schema to accept boolean/null and changed the example to null for unknown state. This evaluator inspected the revised schema/example, updated the actual audit companion to baseline.dirty=null, and removed the forced-false caveat. Revalidation with input hashes returned exit 0 (valid=true, implementation_complete=false, artifact_hashes_checked=true); --require-complete returned the expected exit 1 for an audit. The demonstrated limitation is corrected in the current contract and artifacts.

The contract likewise expects resolved component current values and evidence kinds geared toward publication/compatibility/availability/support/security, so declared local versions and static findings were placed in component reasons and readable prose rather than mislabelled as resolved or verified upstream data. test_jvm=null accurately preserves unknown execution, while the independently specified Java 11 test floor is recorded in policy/constraints because a concrete promised floor differs from an observed JVM.

POLICY.md did not establish an evidence-age limit or mandatory supported-release policy. The fresh report sets evidence_max_age_days=null and require_supported_updates=false instead of inheriting template values; candidates still need compatibility, availability and support review. No public release/support facts were externally verified because network access was expressly prohibited.

This pass validates observable behavior for these four raw inputs, not end-to-end resolution, live mirror access, build/test correctness, real consumer ABI, scanner coverage or candidate freshness. Schema/hash success cannot establish those facts. The evaluator made no repo/fixture changes; the parent applied the dirty-state schema correction separately. Other limitations remain evidence boundaries of the raw offline fixture.

## Correction confirmation

After the parent schema correction, the audit timestamp was refreshed to 2026-10-13T02:09:44Z and both Git revision and dirty state are null. The existing validator and implementation gate were rerun without builds/network access; all four fixture hashes still match the initial observations. This follow-up confirms the corrected report is accepted while an audit still cannot satisfy the implementation gate.
