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

Rendering uses the [templates](../assets/run-templates/index.md), overwrites only the
named generated Markdown documents, and leaves the JSON and evidence unchanged. Write
explanations in phase summaries/notes, not directly in generated Markdown. `check`
verifies the schema, relative paths, dependency graphs, report bindings, local evidence
links, and exact Markdown/JSON consistency. It does not run builds, verify external URLs,
or establish live completion. Report hashes detect drift, not publisher identity.

Keep relative directory structure when sharing the full run and evidence. Individual
timestamped documents can be copied for review, but their relative evidence links need
the corresponding files or deliberately updated published locations. Review content
before committing; do not automatically add raw logs, private metadata, or credentials.
The helper never changes `.gitignore` or stages files. Retain raw evidence under the
organization's existing data policy.
