# Presentation contract

Read this reference before investigation and again when the user asks to revise a generated map. The presentation is a conversational content brief, not a preset picker.

## Build the brief from conversation

Listen for four things in ordinary user language:

1. who will read the map;
2. what that reader should understand, explain, compare, or decide;
3. what must be prominent;
4. what can be merged, hidden, or left for optional drill-down.

The user does not need to know field names or choose a profile. Statements such as "给产品看，重点是每个模块做什么和 Prompt 怎样影响回复，数据库调用可以省略" are already a complete brief. Do not ask the same questions again. When the request only says "generate a map" and different interpretations would materially change the result, ask a short natural-language question about the reader goal and desired emphasis. Avoid a configuration interview when reasonable defaults are sufficient.

Record both the user's meaning and normalized renderer hints in `meta.presentation`:

```json
{
  "audience": "product",
  "detail_level": "standard",
  "focus": ["capabilities", "prompts"],
  "reader_goal": "Understand how each module shapes the user experience and how prompts influence important behavior.",
  "priorities": ["module responsibilities", "prompt effects", "user-visible outcomes"],
  "deemphasize": ["framework plumbing", "ordinary database calls"]
}
```

`reader_goal`, `priorities`, and `deemphasize` are the authoritative authoring brief. `audience`, `detail_level`, and `focus` help the deterministic renderer choose ordering, disclosure, and default visibility. Never reduce a specific user request to only the normalized hints.

Before expensive investigation, summarize the inferred brief in one or two natural sentences when doing so helps the user correct a likely misunderstanding. Do not require formal approval when the request is already clear.

## Fallback hints

Use these only to normalize the brief or supply defaults when the conversation is silent.

### Audience

- `product`: product managers, founders, operators, customers, or non-engineering teammates. Lead with what the system enables, module responsibilities, user-visible outcomes, meaningful decisions, and real prompts. Merge ordinary technical stages and place pipeline diagrams behind progressive disclosure.
- `technical`: engineers, architects, maintainers, or reviewers. Preserve entry points, runtime order, branches, joins, interfaces, state transitions, asynchronous work, and source evidence. Prompts remain visible when they materially control behavior.
- `mixed`: cross-functional onboarding or an unspecified audience. Balance product semantics with enough runtime structure to support engineering follow-up.

Do not infer technical depth merely because the input is source code. Honor explicit user wording such as "给产品看", "architecture review", "focus on prompts", or "only a high-level map". When audience is unspecified, use `mixed`.

### Detail level

- `overview`: fastest orientation. Keep modules and the system story; omit node lists and module pipelines from the main document. The IR still retains enough nodes and evidence to validate the explanation.
- `standard`: system and module views plus collapsed node details. This is the default.
- `deep`: preserve the important technical topology and render node details expanded for close review. Do not turn it into an exhaustive call graph.

Choose the lowest detail level that satisfies the request. The user may combine any audience and detail level, such as `product + deep` for a prompt and policy audit or `technical + overview` for a concise architecture review.

### Focus

Use zero or more supported focus values. They control broad renderer emphasis; they do not replace the free-form priorities.

- `capabilities`: system purpose, module responsibilities, decisions, and outcomes.
- `prompts`: real prompt titles and excerpts, associated with the stage they influence.
- `runtime-flow`: ordering, branches, joins, async dispatch, and feedback.
- `state`: reads, writes, durable artifacts, and state transitions.
- `interfaces`: external systems and cross-module boundaries.
- `source-evidence`: visible repository paths and line ranges.

Defaults:

| Audience | Default focus |
| --- | --- |
| product | `capabilities`, `prompts` |
| technical | `runtime-flow`, `state`, `interfaces`, `source-evidence` |
| mixed | `capabilities`, `runtime-flow`, `prompts` |

If the user explicitly asks to exclude something, record it in `deemphasize`, omit any corresponding broad focus, and subordinate it in the actual model. Never remove evidence required for validation or invent prompts to make a product view more interesting.

## Authoring budgets

These are decision guides, not quotas:

| Profile | Typical modules | Typical nodes | Modeling bias |
| --- | ---: | ---: | --- |
| product overview | 3-6 | 6-14 | capabilities, outcomes, prompt-bearing decisions |
| product standard | 4-7 | 8-18 | semantic stages; merge implementation plumbing |
| mixed standard | 4-8 | 12-24 | product story plus important runtime structure |
| technical deep | 4-8 | 18-30 | topology, state, interfaces, evidence |

Stop adding nodes when they only explain how an already-understood stage is implemented. Increase depth when another node changes the reader's understanding of responsibility, behavior, risk, state, or control flow.

## Apply the brief to content

The brief changes authoring, not only rendering:

- split a module or node when the requested reader needs that distinction;
- merge stages whose differences are implementation-only for that reader;
- retain prompt-bearing decisions when prompts are a priority;
- replace framework labels with domain language when product meaning matters;
- keep requested technical boundaries, branches, state changes, or failure paths explicit;
- omit unsupported or irrelevant sections instead of filling a template.

The IR remains evidence-complete even when the HTML uses progressive disclosure. A request to simplify means simplify the explanation, not discard the source support behind it.

## Revise through dialogue

After delivery, the user may critique any part of the map in ordinary language. Treat that feedback as a delta to the current brief and IR:

1. restate only the changed intent when ambiguity matters;
2. update the free-form brief;
3. remodel the affected modules, nodes, prompts, and relations rather than regenerating unrelated sections;
4. gather new evidence only for newly requested claims;
5. validate and deliver a replacement HTML.

Examples of valid revisions include making one module deeper than the rest, promoting prompt excerpts into the main reading path, collapsing storage plumbing, focusing on failure recovery, or renaming technical concepts in product language. A single document may intentionally have uneven granularity when that matches the reader's goal.
