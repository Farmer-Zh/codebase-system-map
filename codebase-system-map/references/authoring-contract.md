# Authoring contract

Read this reference when converting repository evidence into the System Map IR. Inspect `schemas/system-map.schema.json` before writing: the schema is authoritative for required fields, enum values, formats, and limits.

IR 2.0 has these top-level sections:

```text
meta
system
modules[]
nodes[]
edges[]
sources[]
prompts[]
```

Do not add speculative fields, provider-specific graph objects, or presentation coordinates to compensate for an unclear model.

Set `meta.presentation` from `presentation-contract.md`. Preserve the user's natural-language intent in `reader_goal`, `priorities`, and `deemphasize`; use the enum fields only as normalized renderer hints. Treat the brief as an authoring decision, not a cosmetic theme: it controls which distinctions deserve separate modules or nodes, how labels are phrased, which prompts are promoted, and which content the renderer places first. Evidence requirements do not weaken when technical details are visually subordinate.

## Three-level product model

### System

`system` answers, in plain product language, what the repository enables, what starts its main behavior, and what outcome it produces. It is not a rewrite of the README or a dependency list.

### Modules

Follow the profile budgets in `presentation-contract.md`, but use fewer modules when a small repository has fewer evidence-backed responsibilities. A module is a product capability or coherent runtime responsibility with a meaningful boundary. Several provider clusters, packages, or symbols may collapse into one module; one cluster may split when it contains distinct reader-relevant responsibilities. Name the module by what it does, such as "Request intake" or "Background execution," rather than by a folder, framework, layer suffix, or team name unless that name is itself meaningful to the reader.

Each module needs a concise responsibility and source references. Modules should collectively explain the main behavior without forcing readers to understand packages first.

### Nodes

Keep no more than 30 important nodes, subject to schema limits and the selected detail level. A node is a meaningful stage, decision, store, external dependency, worker, or output - not every provider symbol, class, or function. Merge ordinary linear implementation whenever splitting it would not change the intended reader's understanding.

For every node, describe its purpose, inputs, outputs, module membership, and source references using only schema-supported fields and kinds. Preserve meaningful decision points, fan-out/fan-in, asynchronous dispatch, persistence, feedback, and user-visible results.

Use node kinds consistently:

- **entry** starts a user, API, CLI, event, or scheduled flow;
- **stage** performs ordinary transformation or orchestration;
- **decision** selects a meaningful branch;
- **worker** performs asynchronous or background execution;
- **llm** invokes a language model and is the only kind that may reference prompts;
- **tool** invokes a bounded internal or external capability;
- **store** persists or retrieves durable state;
- **external** represents a material system outside the repository boundary;
- **artifact** is a produced intermediate file, message, or durable object;
- **output** is the user-visible or downstream outcome that closes a flow.

## Edges and primary path

Edges describe behavior or information moving between nodes. Aggregate the provider's symbol-level calls, imports, route links, data flow, and async relations into the smallest reader-meaningful edge. Select types and labels from the schema; keep labels short and meaningful. Avoid duplicating request/response pairs or copying low-level call graphs when one product-level relation explains the interaction.

Mark a clear primary path from at least one entry to at least one user-visible or downstream outcome. The primary path is an evidence-based author judgment, not a claim that other paths are unimportant. It must be continuous and readable. Represent supported branches, merges, asynchronous paths, and feedback explicitly rather than forcing everything into one linear chain.

Every node must connect to the explained system. Aggregate dense external interactions at a meaningful boundary instead of placing every dependency edge in the main view.

## Sources and prompts

`sources` is the centralized evidence table described in `evidence-contract.md`. Other objects reference its IDs rather than duplicating paths and line ranges.

Create a `prompts` entry only for a real LLM prompt or prompt assembly source. Link it to the relevant node and source. Keep any excerpt faithful and limited to what helps explain the node; never expose secrets or invent missing text. Generated HTML may be shared, so include only repository content appropriate for the intended audience.

## Writing quality

- Use the requested language consistently, except for identifiers and source excerpts that should remain exact.
- Lead with observable behavior and responsibility; keep technology names as supporting detail.
- Prefer concrete nouns and verbs over labels such as "core," "manager," "utils," or "processing."
- Do not equate directories with architecture, dependencies with modules, or function calls with product flow.
- Do not claim exhaustiveness. The map is a supported explanation of important behavior, not an index of every file.

Before validation, check that the IR answers the recorded reader goal, honors every priority and simplification, explains one coherent end-to-end story, gives each module a distinct responsibility, supports important claims with evidence, and uses intentionally chosen granularity without contradiction. Uneven module depth is valid when the brief requests it.
