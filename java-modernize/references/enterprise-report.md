# Enterprise evidence report

Use an existing organizational format when it supplies equivalent scope, provenance,
constraints, validation and unresolved-work evidence. Otherwise produce a readable
modernization report and a JSON companion. Never introduce a new approval process merely
to use this format. Keep sensitive reports local according to the existing data policy.

Start from [the example](../assets/enterprise-report.example.json); it intentionally
reports incomplete work and must be filled with actual observations. The formal
[JSON Schema](../assets/enterprise-report.schema.json) uses Draft 2020-12 with local
references only. A generic schema validator checks shape; the bundled helper also
checks cross-field consistency and can verify local artifact hashes.

```sh
python3 <skill-directory>/scripts/validate_report.py <report.json>
python3 <skill-directory>/scripts/validate_report.py <report.json> --project-root <project>
python3 <skill-directory>/scripts/validate_report.py <report.json> --project-root <project> --policy <policy.json> --require-complete
```

The optional helper needs a pre-provisioned Python environment with `jsonschema` 4.x
(Draft202012Validator/FormatChecker APIs, tested locally with 4.19.2). Do not automatically
install packages or contact public registries in a restricted environment. Use the
organization's available validator/manual review if dependencies are missing and record
any consistency checks not performed. The helper itself executes no commands, fetches
no URLs, and prints no report values in schema errors. It supplies its own timestamp
checker; optional missing format-checker dependencies cannot silently bypass dates.

## Contract and interpretation

| Field | Evidence to supply |
| --- | --- |
| `schema_version`, `mode`, `status` | Version 1; audit/upgrade-java/maintain-java/modernize-code; complete/partial/blocked |
| `generated_at` | Actual UTC timestamp, `YYYY-MM-DDTHH:MM:SS[.ffffff]Z` |
| `baseline` | Starting revision when available, pre-existing dirty state (true/false/null for unknown or not applicable), and baseline outcome/limitations |
| `policy` | Actual policy/instruction source, whether supported update releases are required, and the organization's evidence age limit or null if none is established |
| `modules` | Relative module path; observed before/after feature levels for build JVM, compiler JDK, compilation target, test JVM and deployment/minimum consumer runtime; explicit preserved roles |
| `components` | Stable ID, local version-owning file path, observed resolved current version or null, selected candidate or null, update/keep/defer, compatibility/approved-repository availability/support states, reason and dated sources |
| `checks` | Actual command/environment/status, whether the check is required, explanation for non-passing outcomes, artifact IDs and executed test counts for passing test suites |
| `artifacts` | Stable ID, project-relative file path and SHA-256 for version owners, validation logs/reports, dependency graphs, SBOMs and packaged outputs needed to support the conclusions |
| `constraints`, `limitations`, `next_actions` | Requested boundaries, unresolved facts/missing checks, and concrete remaining work |

Optional per-module `targets` binds requested/selected Java feature goals to the relevant
roles (for example, deployment runtime 25 while compilation target remains 17). Complete
implementations must meet every supplied target; a complete Java-upgrade report requires
an explicit API/runtime goal. Copy actual requested goals into these fields, not merely
whatever versions happened to build. Omitted target roles are unconstrained; null is not
a target value.

Use positive integer Java **feature levels**, not `1.8` strings or JDK patch numbers.
Record distribution/patch versions as components. Null means **unknown**, not verified.
For libraries, deployment runtime denotes the supported consumer runtime floor.
Version owners live in the project; describe external BOM/platform ownership in the
component reason and dated evidence. An inherited version's local owner may be the
parent/BOM reference rather than an explicit dependency version.

Each evidence item records kind, sanitized primary-source location, actual check time,
and optionally a captured artifact ID. Distinguish upstream **publication** from
**availability** in the approved repository and from **compatibility**/**support**.
Internal sources are allowed. Evidence cannot postdate the report. Reuse observations
only within the established policy window and while their inputs remain unchanged.

The helper enforces these material invariants:

- IDs within each collection and module paths are unique; referenced artifact IDs exist. Paths remain
  project-relative; hash checks reject symlink artifacts and changed/missing files.
- Maintain-Java and code-only modes preserve known compilation and runtime levels;
  explicitly preserved roles such as test JVM are checked independently.
- Verified freshness has dated publication, compatibility and approved-repository
  availability evidence for assessed components within the configured age limit.
- A passing check has command and artifact evidence. Passing unit/integration tests
  have a nonzero executed count; reduced counts need an actual migration explanation.
  No tests means a justified `not_applicable` outcome, not a passing zero-test suite.
- Complete **implementation** needs verified freshness, known API/runtime targets,
  hashes for assessed version owners, a required passing build, a unit-test outcome,
  every required check passed, and support evidence for updates when policy requires it.

Exit **0** means the report is valid (it may describe incomplete work); **2** means
invalid/inconsistent/unreadable input or missing validator prerequisites. With
`--require-complete`, valid audits and incomplete implementations exit **1**; this gate
requires `--project-root`, checks recorded artifact hashes, and measures evidence age
against actual validation time. Ordinary validation uses the report timestamp so archived
reports remain inspectable. Audits can complete as
audits while honestly reporting unverified candidates and checks not run.

The live gate requires an independently supplied, reviewed project policy, validated
against [the policy schema](../assets/project-policy.schema.json). Adapt
[the policy example](../assets/project-policy.example.json) to actual repository/user
constraints before implementation; never invent organizational requirements. Validate
with `scripts/policy.py <policy.json>`. Pass the same file using `--policy`, and bind
its exact bytes with `policy_binding.sha256` in the report. Store reviewed policy in
version control or supply its immutable trusted copy in CI; the report cannot choose
a weaker file. A hash binds bytes, not reviewer identity or approval.

The policy supplies exact module/component scope, preserved/target Java roles, permitted
actions and selected versions, required check IDs/kinds and permitted outcomes, support
rules, bounded evidence age, and input exclusions with rationale. A report cannot omit
a required consumer/security check by setting its own `required` flag false. Explicit
`not_applicable` is accepted only where policy permits it and the report explains why.
Policy component/version choices still need dated primary-source compatibility evidence.

The live gate additionally requires `inputs_snapshot`: `captured_at`, a map of every
input file to its SHA-256, and `graphs` with module paths and resolved-graph artifact IDs
for every module. Capture after validation with `scripts/snapshot.py <project>` and add
actual graph references; pass `--policy <policy.json>` when capturing custom scope.
An empty graph list is deliberately incomplete. Any added,
deleted or modified input invalidates the gate. The default scope hashes all files,
including wrapper JARs, source/resources, build configuration and deployment/CI files,
except directories named `.git`, `.gradle`, `target`, `build` or `.java-modernize`.
Keep generated reports/logs under `.java-modernize` to avoid hashing the report itself.
Review the policy exclusions; remove any name that contains actual source inputs.
Resolve source directories/symlinks or relevant external settings outside this scope
before claiming coverage. Enumeration/access/size failures reject the gate.

The validator does not execute commands, resolve versions, authenticate sources, discover
external inputs or required checks, assess exception approvals, or establish the truth of reported
results. Reviewers must compare required checks and policy to the actual project. Changes
outside the recorded input/artifact set require renewed review; do not reuse a green
report for a different revision or graph. Package or report validation alone does not
authorize or certify deployment.
