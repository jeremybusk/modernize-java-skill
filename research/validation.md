# Validation of the skill package

Validation performed on 2026-10-12. This repository contains a skill, not a migrated
Java application. Passing package checks is not proof that all downstream projects
will upgrade successfully.

## Executed checks

- `python3 -m unittest discover -s tests -v`: six tests passed. They verify multi-module
  evidence without false version selection, no project changes/build execution, ignored
  caches/symlinks, omission of configuration values, reported unreadable/oversized inputs,
  and nonzero exit status for a missing root.
- The skill-creator `quick_validate.py java-modernize` check passed: supported
  frontmatter, valid name and description, and no unfinished scaffold placeholders.
- Local Markdown link checks passed, and the packaged license/notices match the
  repository copies. The corrected Oracle language-summary URL returned HTTP 200.
- The distribution ZIP was checked for intact contents, all referenced resources,
  metadata, script, license, and third-party notices, with caches excluded.

## Independent behavioral forward evaluation

An independent agent received the completed skill and raw, partial fixtures without
the intended answers or suggested fixes. It produced actual read-only audits for:

1. A Java 11 public library asking for maintenance updates while requiring Java 11
   in production and tests. Its audit retained the runtime constraints and excluded
   a newer test framework requiring Java 17.
2. An application using a Java 21 compiler with a Java 17 API target and runtime,
   a Spring Boot plugin/BOM, a mutated stream result, legacy whitespace checks,
   and a Java SE `javax.sql` import. Its audit represented the Java roles separately,
   preserved BOM ownership and source contracts, and kept the Java SE namespace.

The [actual audit outputs and evaluator findings](forward-evaluation.md) distinguish
verified candidates from unverified support/metadata and checks not run. No demonstrated
skill defect was reported. The evaluator did not modify fixtures, install tooling, or
run missing builds. This single pass provides evidence of instruction behavior on two
audit requests, not a statistical evaluation or cross-agent certification.

## Limits and useful next checks

No complete Maven/Gradle application was migrated, no production service was touched,
and no OpenRewrite artifact or commercial backend was exercised. No JDK 25 compilation
was performed; its feature/API facts were checked against official target-version docs.
The only locally available JDK inspected was Java 21. No actual Codex/Claude/Copilot
installation/discovery matrix was run; installation guidance was checked against
their current official documentation.

Useful future validation on representative applications: a Maven multi-module
Java 8→25 migration; a Gradle catalog/convention-plugin project; a supported Spring
major migration; a same-Java patch-only security update; and an offline audit that
must report unresolved freshness. Validate actual builds, tests, startup, resolved
graphs, and changed contracts in each application's environment.
