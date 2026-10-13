# Java Modernize

A portable Agent Skill for modernizing an existing Java project and keeping its
ecosystem current **even when its Java version stays the same**.

The numbered workflow follows the structure of
[G10xy's Java version upgrade skill](https://github.com/G10xy/java-version-upgrade-skill),
with version-aware code modernization informed by
[Java Evolved](https://github.com/brunoborges/javaevolved) and
[java-code-upgrade](https://github.com/darshitpp/java-code-upgrade), and incremental
validation principles informed by [Microsoft's modernization agent](https://github.com/microsoft/modernize-java).
The instructions and helper are consolidated and rewritten, rather than concatenating
the upstream catalogs. See [the comparison and corrections](research/design-and-provenance.md)
and [primary-source verification](research/verified-ecosystem.md).

## What it covers

- JDK feature migrations and patch/vendor support checks.
- Maintenance while Java is fixed: dependencies, BOMs, frameworks, Maven/Gradle,
  plugins, tests, processors, coverage, agents, CI, and container images.
- Spring Boot/Cloud, Quarkus, Micronaut, Jakarta/server compatibility, persistence,
  serialization, logging, HTTP, JDBC, messaging, and cloud clients when present.
- Final Java idioms available at each module's API target, with contract checks.
- Current release/compatibility evidence, staged edits, baseline comparison,
  test discovery, startup/contract checks, and honest incomplete-verification reporting.
- Enterprise policy and private mirrors, shared-platform/consumer compatibility,
  artifact/SBOM provenance, interrupted-run recovery, and rollback-aware release planning.

## Enterprise use

[Enterprise operation](java-modernize/references/enterprise.md) adds guidance for
approved repositories, support/licensing constraints, existing security exceptions,
API/wire/storage compatibility, and checkpoints that preserve the user's work.
Organization-specific policies and existing authorization control the workflow.
See [enterprise validation and its limits](research/enterprise-validation.md) for the
executed checks, independent offline audit, source verification and remaining coverage.

For substantial enterprise work, the skill produces a readable report and a
[JSON evidence companion](java-modernize/references/enterprise-report.md). The optional
validator checks required evidence, preserved Java targets, test counts, freshness
windows and recorded artifact hashes. Its strict completion gate rejects incomplete
implementations and does not treat a completed audit as a completed migration.

```sh
python3 java-modernize/scripts/validate_report.py /path/to/report.json \
  --project-root /path/to/project --require-complete
```

Report validation needs a pre-provisioned `jsonschema` 4.x environment or equivalent
organizational tooling. The skill/inventory do not require pip dependencies. Validator
success checks the supplied report; human/source/build review still establishes whether
the required checks are complete and the reported outcomes are true.

The repository includes CI for Linux/Windows and Python 3.10/3.14, with a JDK 17 fixture
environment, pinned action commits, read-only permissions, and disabled checkout credential
persistence. It validates inventory, reports, Java API/behavior fixtures, local links,
notices and package integrity. Actual production migrations still require the target
application's tests, policy, deployment environment and release process.

The skill verifies candidates against live sources when invoked; it does not contain
a static list of "latest" versions or run on a schedule. Requested bot configuration
can help with ongoing discovery. OpenRewrite and vendor plugins are optional accelerators,
with exact artifact/access/license checks and manual fallback.

## Install the same folder for your agent

Copy the complete **`java-modernize/`** directory, including its references, optional
script, license, and notices, into a supported skill location. Do not copy only `SKILL.md`.

| Agent | Per-project destination | Personal destination |
| --- | --- | --- |
| Codex | `.agents/skills/java-modernize/` | `~/.agents/skills/java-modernize/` |
| Claude Code | `.claude/skills/java-modernize/` | `~/.claude/skills/java-modernize/` |
| GitHub Copilot | `.github/skills/java-modernize/` | `~/.copilot/skills/java-modernize/` where supported |

Example from this repository, targeting a separate Java project:

```sh
mkdir -p /path/to/java-project/.agents/skills
cp -R java-modernize /path/to/java-project/.agents/skills/
```

Use the corresponding path from the table for Claude or Copilot. Agent releases and
surfaces differ; follow [Codex's current skill documentation](https://learn.chatgpt.com/docs/build-skills),
[Claude Code's skill documentation](https://code.claude.com/docs/en/skills), and
[Copilot's skill documentation](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills)
if a skill is not discovered. Codex's documented current repository/personal locations
are `.agents/skills`; older installations may use legacy `.codex/skills` locations.
The core follows the [Agent Skills format](https://agentskills.io/specification).
No particular MCP server or commercial modernization backend is required.

## Example requests

```text
Use java-modernize to audit this project. Do not edit files yet.

Use java-modernize to keep Java 17 and update compatible dependencies,
frameworks, build plugins, tests, CI, and container images. Verify versions
against current upstream sources and implement the changes.

Use java-modernize to upgrade this Maven project from Java 8 to Java 25.
Preserve application behavior, migrate incompatible dependencies, and run tests.

Use java-modernize to modernize Java idioms while retaining our Java 21 API target.

Use java-modernize to refresh this project and configure our existing Renovate
workflow for ongoing compatible maintenance.
```

Codex also supports `$java-modernize`; Claude Code supports `/java-modernize`.
Natural-language selection depends on the host and skill discovery.

## Files and validation

`java-modernize/SKILL.md` is the entry point. References are loaded only when relevant.
`scripts/inventory.py` is an optional Python 3 helper that lists configuration paths and
line numbers without executing builds, resolving effective versions, making network
calls, modifying the project, or printing configuration values. It can miss custom
configuration; agents must inspect the actual build and resolved graph.
For large repositories, it supports explicit config inclusions, exclusion globs and
configuration-count limits, and reports skipped/pruned/truncated coverage.

```sh
python3 java-modernize/scripts/inventory.py /path/to/java-project
python3 -m unittest discover -s tests -v
```

Helper tests cover preservation of files, no build execution, multi-module evidence,
symlinks/caches, omitted configuration values, and incomplete input reporting. Behavioral
skill evaluation and its limitations are recorded in [validation notes](research/validation.md).
This repository is the skill package, not a Java application; its tests cannot prove
that every downstream project will migrate successfully.

For development, use Python 3.10+ and install `requirements-dev.txt` in a permitted
environment; CI pins the report-validator dependency. JDK 17+ enables the actual
compile/runtime fixture tests. These verify older API targets, class-file levels,
mutability/null/whitespace contracts and unavailable newer APIs. Set
`JAVA_MODERNIZE_REQUIRE_JDK=1` to fail rather than skip them when a JDK is absent.

Build a distribution with an internal SHA-256 file manifest and a companion ZIP checksum:

```sh
python3 scripts/package_skill.py
```

The generated archive is stable for identical inputs in the same Python/zlib environment;
the checksum detects byte changes and is not an authenticity signature. It is written to
`dist/java-modernize.zip` with `dist/java-modernize.zip.sha256`. The development tests,
CI configuration and research notes remain outside the installable skill folder.

## Maintenance and license

When updating the skill, re-check linked official guidance and feature statuses, test
same-Java maintenance and cross-version scenarios, run the helper tests and a skill
frontmatter validator, and preserve third-party notices. Do not blindly sync upstream
pattern catalogs; their preview labels, API examples, and version tables need review.

Apache-2.0 for the combined skill and new helper. MIT notices for upstream materials
are preserved in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md); see [LICENSE](LICENSE).
