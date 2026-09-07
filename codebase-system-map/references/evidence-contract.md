# Evidence contract

Read this reference while investigating the target repository. Its purpose is to keep the resulting map factual, bounded, and traceable.

## Repository boundary and revision

- Resolve one repository root before collecting evidence. Every source path must be relative to that root and must not escape it.
- Record the analyzed Git commit when available. If the working tree is dirty, mark that state in `meta.analyzed_revision`; do not present mutable files as evidence from a clean fixed revision.
- Exclude `.git`, dependencies, vendored code, caches, generated output, build artifacts, coverage output, and historical fixtures unless current runtime evidence proves they participate in the product path.
- Do not include secrets, credentials, private paths outside the repository, or environment values in the IR.

## Bounded investigation

Use the presentation brief to decide where evidence depth is valuable. A request to emphasize prompts warrants following prompt assembly and the decisions those prompts influence; a request to simplify persistence does not warrant cataloguing every repository call. This changes investigation priority, never the requirement that displayed claims remain traceable.

Start with high-signal material:

- README, context, architecture, operations, and deployment documentation;
- manifests, workspace configuration, and executable commands;
- HTTP, CLI, event, scheduler, and worker entry points;
- routing, orchestration, queues, persistence, external systems, and user-visible outputs;
- LLM calls, prompt assembly, tools, and guardrails when they are part of actual behavior;
- implementation links from each important entry to its outcome.

Follow runtime paths until the major responsibilities, branches, joins, asynchronous handoffs, state changes, and outputs can be explained. Do not traverse every file merely for completeness. Use tests as corroboration or to clarify branches, not as the sole evidence for production behavior unless the repository itself is a testing product.

Stop expanding when new files only add implementation detail to an already supported stage. Re-open investigation only when validation identifies a specific missing fact or broken relation.

## What counts as evidence

Create entries in the IR's centralized `sources` table. Each source must identify an existing repository-relative file and a valid, tight line range. Use the schema's supported `evidence_kind` values; do not invent new enum values.

Evidence must directly support the attached claim:

- a module source supports its responsibility or boundary;
- a node source supports that stage's behavior, inputs, or outputs;
- an edge source supports the handoff, call, event, data flow, or transition;
- a prompt source points to the real prompt text or its assembly logic.

Documentation may explain intent, but executable behavior should be corroborated by code or configuration when available. A filename, symbol name, folder name, or dependency declaration alone does not prove runtime behavior.

Reuse one source entry from several claims when the same range genuinely supports them. Prefer several narrow ranges over one entire-file citation. Never fabricate line numbers or cite a range that was not inspected.

## Confidence and ambiguity

Phrase conclusions at the strength of their evidence. Do not turn naming conventions or architectural expectations into facts. When two plausible paths cannot be resolved from the repository, represent the supported ambiguity in the summary or omit the claim; do not choose whichever creates a cleaner diagram.

Every important module and node needs at least one source reference. Important primary and cross-module edges also need evidence. Prompts may only be created for text or assembly logic found in the repository; never reconstruct a supposed prompt from surrounding code.

Before authoring, ensure the evidence can answer:

1. What starts the system's important flows?
2. Which product or runtime responsibilities transform the request or event?
3. Where do meaningful branches, joins, asynchronous handoffs, and state changes occur?
4. What does the user or downstream system receive?
5. Which exact repository ranges support each answer?
