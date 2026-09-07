---
name: codebase-system-map
description: Conversationally design and generate an evidence-backed standalone HTML system map from a real repository. Use when a user wants to decide what a codebase explanation should emphasize, simplify, or omit for product understanding, onboarding, or technical review; not for generic diagrams without source code.
---

# Codebase System Map

Turn the target repository into one offline HTML document shaped for its intended reader. Use the host agent's existing model and repository tools. Do not ask the user for an API URL, key, or model, and do not add a second LLM call.

## Workflow

1. Read [references/presentation-contract.md](references/presentation-contract.md) and establish a presentation brief from the conversation: who will read the map, what they need to understand or decide, what must be prominent, and what may be simplified or omitted. If the request already answers these questions, proceed without asking them again. If a missing choice would materially change the investigation, ask a concise natural-language question; do not make the user configure enum values.
2. Before investigating, run **node <skill-dir>/scripts/system-map.mjs doctor**. If it fails, report the environment diagnostic and stop before doing expensive repository work.
3. Read [references/evidence-contract.md](references/evidence-contract.md), then gather bounded, source-addressable evidence for real runtime behavior rather than cataloguing the directory tree.
4. When ready to model the findings, read [references/authoring-contract.md](references/authoring-contract.md). Write the candidate System Map IR to **<repo>/.codebase-map/system-map.json**; the current shell directory and skill installation directory must not change that target. Never hand-author the final HTML.
5. Read [references/delivery-contract.md](references/delivery-contract.md), validate the candidate, and apply only diagnostic-directed local corrections with at most two repair passes. If errors remain or two consecutive passes do not reduce them, stop and report the unresolved diagnostics instead of claiming success.
6. Once validation passes, deliver **<repo>/generated/<repository-name>/system-map.html** unless the user chose another path. Do not edit generated HTML after delivery.

The document can expose three levels: a concise system overview, one readable view per product or runtime module, and evidence-backed node details. `meta.presentation` records the free-form reader goal, priorities, and simplifications together with normalized rendering hints. The hints are fallbacks, not the product interface. The actual module boundaries, node granularity, prompt selection, labels, ordering, and progressive disclosure must follow the presentation brief. Preserve evidence in the IR even when the brief hides it from the main reading path.

## Conversational revision

Treat feedback on a generated map as an edit request, not as a reason to start over or defend the current profile. Load the existing IR and translate feedback such as "make this module more detailed", "show how these prompts affect the reply", "merge the infrastructure steps", or "hide database plumbing" into an updated presentation brief and corresponding model changes. Update `reader_goal`, `priorities`, and `deemphasize`; then change modules, nodes, prompts, edges, and ordering wherever the requested reading experience requires it. Do not satisfy semantic feedback by only switching `audience`, `detail_level`, CSS, or visibility flags.

Reuse existing evidence when the claim is unchanged. Inspect more source only when the requested content needs new evidence. Validate and deliver again through the normal bounded repair loop, preserving the last-known-good HTML if the revision fails.

The bundled validator, renderer, and assets are local and must not make network requests or start a server. The HTML is the shareable artifact; the IR remains the revisable source.
