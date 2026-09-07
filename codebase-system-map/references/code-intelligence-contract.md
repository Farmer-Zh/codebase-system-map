# Code-intelligence contract

Read this reference before investigating a repository. The code-intelligence
module owns exhaustive structural indexing; this Skill owns reader-shaped
selection and explanation. Keep that seam explicit so the model never has to
ingest the repository file by file.

## Provider interface

A compatible repository-intelligence Skill or MCP provider must supply four
capabilities. Tool names may differ; capability and result shape matter.

1. **Architecture** — repository languages, packages, entry points, routes,
   clusters, boundaries, and high-connectivity symbols.
2. **Search** — locate symbols, routes, prompts, stores, workers, events, and
   configuration by name or product concept without returning whole files.
3. **Trace** — traverse callers and callees or an execution path with symbol,
   relation, file, and line information.
4. **Source slice** — return the smallest source region needed to verify a
   selected symbol or relation.

The provider may index every supported file because indexing happens outside
the model context. Its interface must return bounded, structured results; do
not request a raw graph dump or place all symbols in the prompt.

## Reference provider: Codebase Memory

[Codebase Memory](https://github.com/DeusData/codebase-memory-mcp) is the documented
reference provider. It installs an agent-facing code-intelligence Skill and MCP
server and exposes the required capabilities through these operations:

| Interface capability | Codebase Memory operation |
| --- | --- |
| Index and status | `index_repository`, `index_status`, `list_projects` |
| Architecture | `get_graph_schema`, then `get_architecture` |
| Search | `search_graph` or `search_code` |
| Trace | `trace_path` |
| Source slice | `get_code_snippet` |

Use the project identifier returned by the provider. After indexing, confirm
that the index corresponds to the repository and current revision or working
tree before trusting it.

## Query strategy

Keep model context proportional to the requested map, not repository size.

1. Request one architecture overview.
2. Select candidate entry points and outcomes that match the presentation
   brief.
3. Trace only the candidate flows needed to cover those priorities. Prefer one
   deeper trace over many overlapping shallow traces.
4. Search separately for reader-requested concerns that architecture results
   may underrepresent, such as prompts, background work, persistence, failure
   recovery, or user-visible routes.
5. Retrieve source slices only for nodes and relations likely to enter the
   final map, plus unresolved contradictions.

Stop querying when the important entry-to-outcome paths are supported and new
results only repeat already understood implementation detail. Provider output
is structural evidence, not finished prose; the authoring stage still decides
which symbols should merge into a product or runtime concept.

## Provider substitution

Other code-graph or repository-memory Skills may be used when they satisfy the
same four capabilities. Translate their results at this seam; do not leak
provider-specific objects into the System Map IR.

If the provider cannot parse a relevant language or resolve an important
dynamic edge, record the gap and inspect only that bounded area with ordinary
repository tools. If no compatible provider is installed, tell the user before
using a bounded manual fallback. Never respond to provider absence by reading
the entire repository into model context.
