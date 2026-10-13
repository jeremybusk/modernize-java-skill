# Run documents

Use this contract for substantial modernization work or when the user requests saved
assessment, plan, execution, validation, and completion documents. Honor an existing
equivalent repository convention. A small task can use the compact layout.

## Location and identity

Select the scope root explicitly from the task and repository instructions, never just
the shell's current directory. Use a repository root for one repository, an application
directory for a self-contained application scope, or a common workspace directory for
several repositories. If shared parents/platforms outside an application own changes,
expand the recorded scope accordingly. Do not create a synthetic Git repository.

The helper creates `.java-modernize/runs/<run-id>/` under that root. The run ID contains
the actual UTC creation time with microseconds and a short slug, for example
`20261013T183012123456Z-java-maintenance`. Every Markdown filename and the run manifest
begin with this ID, so copying a plan or summary into reviewed repository documentation
retains its identity. Filenames stay stable as the run progresses; `updated_at` records
edits. A separate invocation starts a new run; resuming uses the existing manifest.

```sh
python3 <skill>/scripts/run_documents.py init \
  --scope-root /path/to/project --repo app=. --slug java-maintenance
```

The expanded layout produces timestamp-prefixed `index.md`, `assessment.md`, `plan.md`,
`execution.md`, `validation.md`, `completion-summary.md`, and `run.json`. With
`--layout compact`, it produces `index.md`, `report.md` containing all five phases, and
`run.json`. Use `--mode audit` for an assessment without implementation. Creating saved
documents is itself a filesystem edit: for an explicitly read-only/no-files audit,
return the report in the conversation unless an external output location was authorized.
Choose the layout at initialization; changing layouts later requires a new run so older
generated summaries cannot silently remain alongside a conflicting current document set.

For a coordinated workspace:

```sh
python3 <skill>/scripts/run_documents.py init \
  --scope-root /path/to/workspace --scope-kind workspace \
  --repo platform=platform --repo service=services/orders --slug coordinated-upgrade
```

Repository paths are relative to the selected root. Each scope has a stable ID and
independent baseline, report, and checkpoint. Represent overlapping Maven/Gradle modules
in one repository report rather than counting their inputs twice. Record repository
and batch dependencies by ID; cycles and unknown IDs are rejected. Choose a common
ancestor explicitly when repositories are siblings. The helper does not search for,
clone, edit, commit, or publish additional repositories.

`.java-modernize/latest.json` points to the most recently initialized run. It is a
convenience pointer, not the most recently completed run or a source of completion
authority. Concurrent runs keep independent directories; the last pointer write wins.
No symlink is required. Open the named manifest for resuming or validating a specific run.

## Authoring and rendering

The [run schema](../assets/run.schema.json) defines phase summaries/notes, findings,
testable batches with recovery boundaries, dependencies, the next action, deployment
status, and repository mappings. Initialize the real run rather than copying invented
observations. Edit its JSON to record actual findings and decisions; update `updated_at`
to the actual UTC time. Free-text fields render as text rather than executable Markdown.
Use `repository:path` in batch file lists and record commit IDs in batch results.
The optional `links` array takes `label` and HTTP(S) `url` entries for commits, CI results,
reviews, and releases. It generates clickable completion links; the helper does not fetch
them or infer successful CI/deployment from their presence. Dated source links render
from component evidence. Each Markdown file includes a title and machine-readable YAML
frontmatter identifying the run, phase, recorded status, update time, and JSON manifest.

Each repository's `report` is null until available, then contains a project-relative
`path` and the exact file `sha256` of its [enterprise evidence report](enterprise-report.md).
Version tables, Java targets, checks, counts, constraints, limitations, and remaining
actions render from those bound reports. Keep the evidence report inside the repository's
`.java-modernize` directory so it is excluded from source snapshots. Missing information
is displayed explicitly; empty lists never establish passing checks or absence of risk.

```sh
python3 <skill>/scripts/run_documents.py render /path/to/<run-id>-run.json
python3 <skill>/scripts/run_documents.py check /path/to/<run-id>-run.json
```

Use `bind-report <manifest> --repo <id> --report <project-relative-path>` after reviewing
each new evidence report; it computes the hash and rerenders. Rebinding never runs or
repairs the report's checks. Keep baseline revision/dirty observations consistent with
the run's initial observations. Bind reports before marking validation/completion complete.

Rendering uses the [templates](../assets/run-templates/index.md), overwrites only the
named generated Markdown documents, and leaves the JSON and evidence unchanged. Write
explanations in phase summaries/notes, not directly in generated Markdown. `check`
verifies the schema, relative paths, dependency graphs, report bindings, local evidence
links, and exact Markdown/JSON consistency. It does not run builds, verify external URLs,
or establish live completion. Report hashes detect drift, not publisher identity.

## Evidence, checkpoints, and resumption

Pass `--run-id <run-id>` to `collect_evidence.py` to retain each execution under
`<repository>/.java-modernize/runs/<run-id>/evidence/<check-id>/`. For a workspace,
use the workspace's run ID in every repository, but execute each command with its actual
repository root and independent policy. Artifact paths remain relative to that repository;
do not move evidence and silently rewrite hashes. Existing invocations without `--run-id`
retain their legacy output location. A check ID must be unused within its run; retries
need a new ID and the corresponding reviewed policy/check mapping where applicable.

After recording a reviewed baseline or a finished batch, save a checkpoint:

```sh
python3 <skill>/scripts/run_documents.py checkpoint /path/to/<run-id>-run.json \
  --policy app=/path/to/reviewed-policy.json
python3 <skill>/scripts/run_documents.py resume /path/to/<run-id>-run.json \
  --policy app=/path/to/reviewed-policy.json
```

Supply one `--policy ID=file` for each customized repository scope. Without a policy,
checkpoint/resume use the documented default snapshot exclusions. The same policy bytes
and exclusions must be supplied when resuming. Checkpoints record input hashes, revision,
policy digest, and capture time in a new timestamped file; old checkpoints remain intact.

`resume` compares current inputs, revision, policy, and report bytes. Missing/unreadable
checkpoints mean unknown state, not unchanged state. Changes invalidate active/completed
phases and affected batches, including dependent repositories/batches, and set an explicit
next action. It never resets files, replays edits, runs builds, or refreshes evidence.
Retained reports describe their earlier state. If a bound report changed, review it and
bind it again before rendering; the helper does not bless the new bytes automatically.
Exit 0 means the checkpoint comparison found no changes, 1 means scope needs reassessment,
and 2 means an invalid invocation/manifest or unavailable prerequisites. Unchanged inputs
do not prove that upstream candidates or time-limited evidence remain current.

## Phase and completion rules

Record phase status as `pending`, `in_progress`, `complete`, `blocked`, or `stale` with
a summary for every non-pending phase. Completed phases require completed predecessors.
Only audit execution/validation may use `not_applicable`, with a reason. Implementation
plans need testable batches covering each repository; a no-op is a completed batch with
an evidence-backed result and no changed files. Batch dependencies must complete first.

Keep phase explanations concise and specific:

| Phase | Record |
| --- | --- |
| Assessment | Scope/exclusions, baseline failures, constraints, stable finding IDs, owners, verified candidate sources, and unknowns. |
| Plan | Ordered batch IDs, dependencies, intended behavior, files, success criteria, affected contracts, and recovery boundaries. |
| Execution | Actual edits, deviations and their reasons, batch results/commit IDs, checkpoint, blockers, and next action. |
| Validation | Required commands/environments, baseline versus current test counts, outcomes, retained evidence, and unavailable checks. |
| Completion | Outcome, before/after including fixed Java targets, verified changes, remaining work, recovery, and deployment status. |

`check` is an archival consistency check. A completed audit remains an audit. A completed
implementation requires all phases and repository reports complete; to check **current**
completion, run the live gate with independently supplied policies:

```sh
python3 <skill>/scripts/run_documents.py check /path/to/<run-id>-run.json \
  --require-complete \
  --policy platform=/path/to/reviewed-platform-policy.json \
  --policy service=/path/to/reviewed-service-policy.json
```

The helper invokes the existing report validator for every repository, including current
inputs, artifact hashes, recorded processes, test counts, graph coverage, policy bindings,
and freshness windows. A missing policy, incomplete repository, changed input, stale
evidence, or Markdown drift rejects the overall gate. It does not execute report commands.
It does not certify deployment, business acceptance, or authenticity of local records.
Deployment status remains separately recorded and requires actual external evidence.

JSON parsing/schema validation requires pre-provisioned `jsonschema` 4.x, as with the
enterprise report validator. There are no automatic package installs or network calls.
If the helper is unavailable, use the same templates and contract with existing tooling;
report which automated consistency/live checks were not run.

Keep relative directory structure when sharing the full run and evidence. Individual
timestamped documents can be copied for review, but their relative evidence links need
the corresponding files or deliberately updated published locations. Review content
before committing; do not automatically add raw logs, private metadata, or credentials.
The helper never changes `.gitignore` or stages files. Retain raw evidence under the
organization's existing data policy.
