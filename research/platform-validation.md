# Platform and CI validation

Checked 2026-10-13. This file records executed results and distinguishes pending runs.

## Dependency lock

Resolved the Python 3.10-compatible closure of jsonschema 4.26.0 and PyYAML 6.0.3:
attrs 26.1.0, jsonschema-specifications 2025.9.1, referencing 0.37.0, rpds-py 0.30.0,
and typing-extensions 4.16.0. rpds-py 2026.9.1 requires Python 3.11+, so it was excluded.
Official PyPI release metadata supplies every committed non-yanked wheel SHA-256.

All four wheel-download checks passed with `--require-hashes --only-binary=:all:`:
CPython 3.10 and 3.14, Linux x86-64 and Windows AMD64. Installed the exact lock into
an isolated temporary Python 3.14 environment; 46 default tests passed, six opt-in
integrations skipped. Wheel resolution checks do not execute Windows/Python 3.10 tests;
the hosted matrix supplies those runtime checks.

Source: [pip secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/),
[rpds-py 0.30.0 metadata](https://pypi.org/pypi/rpds-py/0.30.0/json),
[rpds-py 2026.9.1 metadata](https://pypi.org/pypi/rpds-py/2026.9.1/json).

## Provisioning and hosted execution

Verified Gradle 8.14.3 distribution SHA-256
`bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531` against
[Gradle's published checksum](https://services.gradle.org/distributions/gradle-8.14.3-bin.zip.sha256)
and successfully downloaded/extracted it with the integration bootstrap. JDK pins and
checksums are documented in [integration sources](integration-sources.md).

Pinned `actions/upload-artifact` v7.0.2 to commit
`cf430e030ddbb5b0abf93d22962f4752f3646cd9` using the official release/tag API.
The workflow retains synthetic logs/results and archives for 14 days with read-only
repository permissions and no persisted checkout credentials.

Maven is pinned to 3.9.12 so an updated runner default cannot silently require a newer
JVM than the Java 8 baseline. Its SHA-512 was checked against
[Apache's archive checksum](https://archive.apache.org/dist/maven/maven-3/3.9.12/binaries/apache-maven-3.9.12-bin.tar.gz.sha512).
The freshly downloaded Maven/Gradle distributions both passed actual migration runs:
Java 8 to 25 reactor and Gradle catalog maintenance, including tests, startup and stable
reruns. These local runs used cached dependencies in offline build mode.

The configured repository is now `jeremybusk/modernize-java-skill`. Hosted validation
of step 4 commit `ec9504a01f3ca34a0aa66de44a584389ed7bf03b` already passed:
[baseline CI run](https://github.com/jeremybusk/modernize-java-skill/actions/runs/38407811260).
The expanded step 5 workflow is pending its own committed hosted execution.

## Real agent evaluations

Each CLI receives an identical synthetic task with the same skill installed under its
documented project skill directory. Evaluations explicitly name the skill path and
restrict the requested work to local reads/edits. No conclusion about automatic routing,
IDE extensions or other models follows from these tests. CLI defaults select the model;
local raw logs retain provider-specific details where exposed.

- Claude Code 2.1.270: corrected private-parent audit passed without changing inputs or
  inventing a selected release. The exact Boot 3.5.15 to 3.5.16 edit passed; only pom.xml
  changed. Independent Maven 3.9.12/Java 21.0.12.1 validation executed one test before
  and after, kept Java 17 bytecode, and passed both packaged HTTP startup checks. The
  repeated agent request made no further input changes.
- Codex CLI 0.162.1: corrected private-parent audit and exact patch both passed. The
  independent Maven/Java checks match the Claude results above; the repeated request
  made no additional input changes. The first fixture setup failed to substitute the
  private coordinate; that setup was fixed and the corrected case was rerun successfully.
- Copilot CLI 1.0.88: both tasks passed with independent Maven tests, Java 17 bytecode,
  packaged HTTP startup before/after and a stable agent rerun. The first invocation
  lacked the model's `apply_patch` tool in the harness allowlist. Copilot honestly reported
  it could not write files. Adding the documented patch tool fixed the harness; both
  complete evaluations then passed.

Observed provider metadata identifies Claude Sonnet 5 (plus Haiku 4.5 service usage)
and Copilot's GPT-6 Luna. Codex's JSON event stream did not expose a model identity;
its CLI/default configuration is recorded without inventing that detail. Evaluation
results are bounded observations for these installed versions and tasks.

Raw agent responses are retained locally instead of committing session/account metadata.
The offline task requires unknown freshness/build results to remain unverified/not run;
external evaluator validation is recorded separately from the agent's own claims.

Sources: [Codex non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode),
[Claude programmatic execution](https://code.claude.com/docs/en/headless),
[Copilot tool permissions](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/allowing-tools).
