# Codebase System Map

> Give a coding agent a repository. Get one product-readable, evidence-backed system map.

[Website & live showcases](https://farmer-zh.github.io/codebase-system-map/) · [简体中文](README.zh-CN.md)

Codebase System Map is an open-source Agent Skill for codebase visualization,
software architecture documentation, and developer onboarding. It guides a
repository-aware coding agent to turn real source behavior into one standalone
HTML document that product managers, founders, operators, and engineers can
read.

- **Audience-shaped:** tell the agent who will read the map and what matters.
- **Conversational:** refine modules, detail, terminology, and emphasis in
  ordinary language.
- **Evidence-backed:** important claims link to repository files and line
  ranges.
- **Offline and shareable:** the final HTML needs no server, CDN, or account.
- **No second LLM setup:** the Skill uses the coding agent you already have.

~~~text
Repository
  → agent follows important runtime paths
  → evidence-backed System Map IR
  → local validation
  → standalone system-map.html
~~~

The agent and terminal can be closed after generation. The HTML will continue
to work as a single offline file.

![Workflow: choose the reader, follow source evidence, and open one standalone HTML](docs/assets/workflow.gif)

## What the map shows

The document has three progressively detailed levels:

1. **System overview** — what the repository enables, its major
   responsibilities, and one clear end-to-end path.
2. **Module views** — meaningful product or runtime modules, their boundaries,
   and the important flow between them.
3. **Node details** — purpose, inputs, outputs, source evidence, and real prompt
   excerpts when the repository contains LLM prompts.

This is not a directory tree, dependency inventory, or exhaustive call graph.
The map explains the parts that matter for the stated reader goal.

## Showcases

Each showcase was generated from a fixed public commit and is available as a
standalone HTML plus its revisable IR.

| Repository | Reader goal | Result |
| --- | --- | --- |
| [Huey](https://github.com/coleifer/huey) | Technical view of task declaration, queues, scheduling, workers, retries, and results | [HTML](showcases/huey/system-map.html) · [IR](showcases/huey/system-map.json) |
| [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template) | Product view of sign-up, sign-in, account recovery, and the owned-items experience | [HTML](showcases/full-stack-fastapi-template/system-map.html) · [IR](showcases/full-stack-fastapi-template/system-map.json) |
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | Mixed view of the run loop, tools, handoffs, guardrails, sessions, tracing, and a real handoff prompt | [HTML](showcases/openai-agents-python/system-map.html) · [IR](showcases/openai-agents-python/system-map.json) |

Download an HTML file and open it in a modern browser to use it offline.
Repository, commit, license, presentation brief, and generation counts are
recorded beside each example in metadata.json.

## Quick start

### Requirements

- A coding agent that can inspect the target repository and run local commands.
- Node.js 18 or newer.
- Git is optional, but recommended so the map can record the analyzed revision.

The bundled validator and renderer have no package-install step and make no
network requests.

### 1. Clone

~~~bash
git clone https://github.com/Farmer-Zh/codebase-system-map.git
cd codebase-system-map
~~~

### 2. Install the Skill

For a local Codex installation on Windows PowerShell:

~~~powershell
$skillPath = Join-Path $env:USERPROFILE ".codex\skills\codebase-system-map"
New-Item -ItemType Directory -Force $skillPath | Out-Null
Copy-Item -Path ".\codebase-system-map\*" -Destination $skillPath -Recurse -Force
~~~

On macOS or Linux:

~~~bash
mkdir -p "$HOME/.codex/skills/codebase-system-map"
cp -R codebase-system-map/. "$HOME/.codex/skills/codebase-system-map/"
~~~

Open a new agent session after installing or updating the Skill so the
available-skill list refreshes.

For another Agent Skills-compatible coding agent, install the
codebase-system-map directory using that product's Skill discovery mechanism.
The entry point is [SKILL.md](codebase-system-map/SKILL.md).

### 3. Ask for the map you need

For product understanding:

~~~text
Use codebase-system-map on this repository.
Create a standard map for product managers. Emphasize what each module does,
the user-visible outcomes, and any real prompts. Simplify framework and
database plumbing.
~~~

For a technical review:

~~~text
Use codebase-system-map on this repository for engineers.
Use deep detail. Preserve runtime order, branches, asynchronous work, state
changes, external interfaces, and source evidence.
~~~

If the target is elsewhere, provide its path in the request. You can also
request a language or output location explicitly.

Without a language override, the agent follows the language of the
repository's primary documentation.

## Shape the result through conversation

There is no fixed product/technical template that decides everything. The
agent turns your wording into a presentation brief and changes the actual
model: module boundaries, node granularity, names, prompts, relations, order,
and progressive disclosure.

After seeing the first result, continue with requests such as:

~~~text
Make the payment module more detailed, but merge ordinary database calls.
~~~

~~~text
Show how these two prompts affect the final reply. Hide source paths from the
main reading path, but keep their evidence in the IR.
~~~

~~~text
This is for customer-success onboarding. Rename technical stages in product
language and focus on failure recovery.
~~~

The agent revises the existing IR, gathers only newly needed evidence, validates
again, and atomically replaces the HTML. Different modules may intentionally
use different levels of detail.

## Output

The default files are:

~~~text
<target-repository>/.codebase-map/system-map.json
<target-repository>/generated/<repository-name>/system-map.html
~~~

- system-map.json is the evidence-backed, revisable source.
- system-map.html is the file to open or share with readers.

The HTML embeds its graph renderer and WebAssembly. It starts no local server
and makes no runtime network request. JavaScript must be enabled for diagrams;
all document content remains inside the file.

## How it stays reliable

The Skill requires the agent to:

1. establish the repository boundary and analyzed Git revision;
2. follow real runtime paths instead of cataloguing every file;
3. cite tight repository-relative source ranges for important claims;
4. create prompts only when real prompt text or assembly logic exists;
5. validate schema, references, topology, entry/output nodes, and the primary
   path;
6. apply at most two diagnostic-directed repair passes;
7. render only after validation succeeds.

Delivery is atomic. A failed validation or render does not overwrite the last
known-good HTML.

## Manual diagnostics

The agent normally runs these commands. To inspect a result yourself, run them
from the installed Skill directory:

~~~bash
node scripts/system-map.mjs doctor
node scripts/system-map.mjs validate "/path/to/system-map.json" --repo "/path/to/repository" --json
node scripts/system-map.mjs deliver "/path/to/system-map.json" "/path/to/system-map.html" --repo "/path/to/repository" --json
~~~

Quote Windows paths that contain spaces.

## Privacy and limitations

- Source inspection and final rendering happen locally through the host agent.
- The bundled validator and renderer do not call an LLM or external service.
- Generated HTML and IR may expose repository paths, system behavior, and
  prompt excerpts. Review them before publishing or sharing outside your team.
- The result is a bounded explanation of important behavior, not proof that
  every runtime path was found.
- Source evidence supports the explanation at the analyzed revision. Regenerate
  after material repository changes.
- Prompt cards are shown only for real repository prompts; non-LLM projects
  correctly produce no prompt section.

## Repository layout

~~~text
codebase-system-map/
  SKILL.md                         agent workflow
  agents/openai.yaml               Skill metadata and default request
  references/                      presentation, evidence, authoring, delivery
  schemas/system-map.schema.json   System Map IR 2.0
  scripts/system-map.mjs           doctor, validate, deliver
  assets/                          offline graph renderer and license
showcases/
  manifest.json                    fixed revisions and presentation briefs
  <case>/                          standalone HTML, IR, metadata
tests/
  system-map-cli.test.mjs          deterministic validator/renderer tests
DESIGN.md                          visual direction
~~~

## Development

Run the deterministic test suite with Node.js 18 or newer:

~~~bash
npm test
~~~

The test suite covers environment checks, IR validation, presentation behavior,
standalone delivery, and preservation of the last-known-good output.

## Open-source components

The project deliberately keeps its implementation small. The validator,
delivery CLI, and GitHub Pages site use only Node.js built-in modules and plain
HTML, CSS, and JavaScript. Generated HTML bundles these third-party components
so diagrams continue to work offline:

| Component | How it is used | License |
| --- | --- | --- |
| [Viz.js 3.29.0](https://github.com/mdaines/viz-js) | JavaScript wrapper and WebAssembly graph renderer embedded in every HTML file | MIT |
| [Graphviz](https://graphviz.org/) | DOT layout and SVG generation inside the Viz.js WebAssembly build | Eclipse Public License 2.0 |
| [Expat](https://github.com/libexpat/libexpat) | XML parser included transitively in the Viz.js object-code distribution | MIT |

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the complete license
texts in [codebase-system-map/assets/licenses](codebase-system-map/assets/licenses/).

## License

[MIT](LICENSE). Third-party components remain under their respective licenses.
