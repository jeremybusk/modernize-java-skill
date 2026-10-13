# Validation and reporting

Establish a baseline before mutation where tools are available, then validate each
coherent batch and the final state. Required checks follow the repository and changed
behavior; do not add unrelated quality gates or manufacture a green result.

## Build and runtime evidence

- Use wrappers, profiles, modules, and toolchains actually intended for CI/deployment.
  Inspect the project's commands first. Typical final commands are `./mvnw verify`
  or `./gradlew build`; Gradle integration-test tasks and startup/smoke tests are often
  separate. `test-compile` is not test execution. A successful `verify` does not prove
  integration tests ran if Failsafe/profiles were not configured.
- Confirm both production and test code compile, annotation processors run, and
  expected artifacts/generated sources are packaged. Inspect the resolved graph for
  mismatched managed/transitive versions, shaded libraries, conflicting logging
  providers, and unwanted namespace mixtures in affected APIs.
- Compare discovered/executed/skipped test counts before and after engine migrations.
  Zero discovered tests can look green. Preserve engine configuration until its tests
  are migrated. Investigate newly disabled tests or changed assertions.
- Exercise affected contracts: charset/locale/tzdata, JSON/XML/persistence, TLS/auth,
  reflection/service loading, native libraries/agents, transactions/messaging/retries,
  and application startup in the intended runtime/image.
- For a library promising older Java, compile against its API target and test on the
  minimum runtime, even if the build/test tools themselves need a newer JVM. Separate
  test-tool JVM requirements from consumer runtime requirements.
- Run existing vulnerability/SBOM checks when applicable; confirm database freshness
  and relevant resolved/transitive/image coverage. Record unavailable scan evidence.
- Compare performance/resource use for changes likely to affect it using an existing
  representative workload. Compile/test success does not prove a speed improvement.

Fix regressions introduced by the migration. Separate pre-existing failures with baseline
evidence. Missing infrastructure, credentials, tools, or a required runtime can leave
verification incomplete: record the blocker and exact next check instead of disabling
tests or asserting success. Testing a production deployment requires its own scope.

For enterprise runs, apply the actual policy/consumer requirements in
[enterprise operation](enterprise.md) and include the source/evidence/checkpoint information
from [the report contract](enterprise-report.md). A report validator checks submitted
claims and file hashes; it does not execute or independently prove the listed checks.

## Report shape

Use existing repository reporting conventions. For substantial work, a single report
with the following content is enough; create extra plan/progress files only if useful.
For requested saved documents or substantial runs, use the compact or expanded
[timestamped run templates](run-documents.md). The run helper renders repeated facts from
the JSON evidence companions and checks that the Markdown remains consistent.

1. **Scope and Java settings:** mode, constraints, per-module build/compiler/release/
   test/deployment JVMs before/after, including explicitly unchanged settings.
2. **Version evidence:** current declared/resolved, selected exact candidate, version
   owner, primary source and date, exclusions (newer incompatible, prerelease, unsupported,
   unverified), and why platform/security overrides remain or were removed.
3. **Changes:** files and observable behavior, required migrations versus optional
   idioms, temporary configuration and its removal condition.
4. **Validation:** commands, intended JVM/environment, baseline and resulting outcomes,
   test counts where relevant; label passed/failed/not run/not applicable.
5. **Remaining items:** unresolved constraints, unverified facts, behavior risks,
   external checks and follow-up recommendations. Never label implementation complete
   when requested work remains or the build fails because of the changes.

For an audit, give actionable proposals and verification commands and explicitly say
the files have not been changed. For an evidence-backed no-op, name which components
and sources were checked. A future scheduled/bot workflow is not proof of current freshness.
