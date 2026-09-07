# Delivery contract

Read this reference after a complete candidate IR exists. Validation and rendering are deterministic local operations; they do not call an LLM, contact a service, or start a server.

## Paths

Use these defaults unless the user requested another output location:

```text
<repo>/.codebase-map/system-map.json
<repo>/generated/<repository-name>/system-map.html
```

Treat the JSON as the revisable source and the standalone HTML as the only file a reader needs. Quote paths in shell commands, especially on Windows.

## Validate and repair

From the skill directory, run:

```text
node scripts/system-map.mjs doctor
node scripts/system-map.mjs validate "<candidate.json>" --repo "<repo>" --json
```

Use the process exit code and JSON diagnostics, not console wording, to decide whether validation passed. Diagnostics should identify a stable code, subject, evidence, and supported fixes.

If validation fails:

1. Save the diagnostic set.
2. Correct only the facts and references named by diagnostics; inspect additional source only for those corrections.
3. Re-run validation and compare diagnostic errors.
4. Perform no more than two repair passes.

Stop early if a pass leaves the same errors or does not reduce the error set. Report the unresolved diagnostic codes and subjects. Do not weaken evidence, delete a supported branch merely to satisfy layout, bypass validation, or claim that HTML was delivered.

Warnings may be reported with a successful result if the validator classifies them as non-blocking. Do not silently reinterpret an error as a warning.

## Deliver

After validation succeeds, run:

```text
node scripts/system-map.mjs deliver "<candidate.json>" "<output.html>" --repo "<repo>" --json
```

`deliver` revalidates before rendering and is responsible for atomic replacement. Never hand-edit its HTML output. If delivery fails, preserve any last-known-good HTML, report the failing stage and diagnostic, and leave the validated candidate available for retry.

The delivered HTML must remain standalone and usable after the agent and terminal close. Do not launch or leave behind a web server, watcher, or background process.

## Handoff

On success, tell the user:

- the absolute path to the HTML;
- the absolute path to the source IR;
- the output language and analyzed revision or dirty-worktree status;
- the selected audience, detail level, and explicit focus;
- any non-blocking warnings or intentionally omitted areas;
- that the HTML can be opened and shared offline.

Before suggesting external publication, remind the user that the HTML and IR can expose repository paths, system behavior, and prompt excerpts. Publication or upload is a separate action and requires the user's request; local generation does not authorize it.
