# Automation choices

Choose tools already used by the project when suitable. Tools accelerate mechanical
work; they do not replace release verification, diff review, or behavior tests.

## OpenRewrite

1. Find a recipe matching the exact source/target and requested scope in the
   [official catalog](https://docs.openrewrite.org/recipes). Verify its recipe ID,
   options, artifact coordinates/version, minimum Java/build-tool requirements,
   dependencies, license, repository, and available access.
2. Pin a mutually compatible plugin and recipe artifact. A recipe YAML alone may
   reference Java recipe classes needing their own artifacts. Do not assume installing
   `rewrite-maven-plugin` loads every migration recipe or that it supports Gradle.
3. Use the documented Maven/Gradle plugin configuration or an existing init-script
   workflow. Verify actual discovery with `rewrite:discover` / `rewriteDiscover` when
   those tasks/goals are available. Run a dry run (`rewrite:dryRun` / `rewriteDryRun`)
   before apply (`rewrite:run` / `rewriteRun`) where supported.
4. Review affected files, recipes run, generated reports, managed version changes,
   syntax/API contracts, and unexpected dependencies. Then run normal project checks.
5. Remove temporary configuration only if it was introduced solely for this run and
   is no longer useful; preserve existing project migration tooling.

The current [Java 17 recipe guide](https://docs.openrewrite.org/running-recipes/popular-recipe-guides/migrate-to-java-17)
documents changing artifact availability and access requirements. Verify the exact
selected version at execution time. Do not assume current binaries are anonymously
available on Maven Central, add credentials, buy a service, or add a new authenticated
repository without the needed access/authorization. Manually apply the required changes
or use an already available supported tool when recipe artifacts are unavailable.

Read plugin instructions for the selected versions:
[Maven configuration](https://docs.openrewrite.org/reference/rewrite-maven-plugin),
[Gradle configuration](https://docs.openrewrite.org/reference/rewrite-gradle-plugin).
Avoid copy-pasting an unpinned command from an old skill or letting a rolling catalog
choose versions in a supposedly reproducible migration.

## Other tools

Framework update tools (such as Quarkus update), compiler diagnostics, JDK bytecode tools,
and existing IDE inspections are useful when they support the detected project.
Use source-aware transformations rather than global regex changes to Java or namespaces.

Microsoft's [Java modernization plugin](https://github.com/microsoft/modernize-java)
offers a Copilot-specific planning/execution environment. If the user already selected
it and its tools are available, it can assist. The portable skill does not require its
session IDs, telemetry hooks, custom version-control tool, or proprietary backend.
Do not invoke one entry-point repeatedly if it redirects back to the active agent.
Keep the same version evidence, scope, contract, and validation standards for tool output.
