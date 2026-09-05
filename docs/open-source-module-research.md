# Codebase System Map：可复用开源模块调研

> 调研快照：2026-09-04  
> 范围：只使用项目官方文档、官方 GitHub 仓库和许可证文件。许可证判断不是法律意见；实际发布前仍应对锁定版本及其传递依赖做一次 SBOM/许可证审查。

## 结论

这个项目不需要自行实现解析器、代码图数据库、Tracing 平台或浏览器图引擎。建议把真正自有的部分缩到三件事：

1. `system-map.json` 的领域模型与证据规则；
2. 将各类开源工具结果归一化为该模型的 Adapter；
3. 从实现事实和运行证据推导 Flow / Stage / Prompt / Tool / Artifact 的合并逻辑。

推荐按两期引入开源模块。

### 静态 MVP 的最小组合

| 环节 | 默认模块 | 采用理由 | 许可证 / 边界 |
|---|---|---|---|
| 代码轮廓、Prompt/LLM/Tool 调用发现 | [ast-grep](https://github.com/ast-grep/ast-grep) | 基于 Tree-sitter 做结构化代码匹配；YAML 规则可由本项目维护；CLI 能输出包含文件、源码范围和 metavariable 的 JSON，并有 `outline` 输出符号、import/export 和成员。[JSON 输出结构](https://ast-grep.github.io/guide/tools/json)、[outline 限制](https://ast-grep.github.io/guide/outline-code) | MIT，[LICENSE](https://github.com/ast-grep/ast-grep/blob/main/LICENSE)。它只给本地语法事实，不解析类型、跨文件引用或调用图，因此不能单独承担 Implementation Graph。 |
| 多语言调用图 / 数据流增强 | [Joern](https://github.com/joernio/joern) | 将不同语言归一为 Code Property Graph；官方查询支持 caller/callee/call-site，且能导出 GraphML、GraphSON、Neo4j CSV 等格式。[支持语言与成熟度](https://docs.joern.io/)、[Call Graph 查询](https://docs.joern.io/cpgql/complex-steps/)、[图导出](https://docs.joern.io/export/) | Apache-2.0，[LICENSE](https://github.com/joernio/joern/blob/master/LICENSE)。作为独立 CLI/容器调用，不把其内部 CPG 类型泄露到领域模型。 |
| 构建期图合并、遍历和影响分析 | [NetworkX](https://github.com/networkx/networkx) | 成熟的 Python 图结构与算法库，足以做 descendants、最短路径、拓扑排序、强连通分量和 blast radius；无需先部署图数据库。 | BSD-3-Clause，[LICENSE](https://github.com/networkx/networkx/blob/main/LICENSE.txt)。图的持久事实仍写入 `system-map.json`。 |
| Schema 与构建阻断 | [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) + [python-jsonschema](https://github.com/python-jsonschema/jsonschema) | 标准 Schema 作为工具间契约；`python-jsonschema` 完整支持 Draft 2020-12，并能逐项报告验证错误。[官方功能说明](https://github.com/python-jsonschema/jsonschema#features) | MIT，[项目元数据](https://github.com/python-jsonschema/jsonschema/blob/main/pyproject.toml)。若启用格式校验，优先 `format-nongpl`，官方文档提示普通 `format` extra 可能引入 GPL 依赖。[格式校验说明](https://github.com/python-jsonschema/jsonschema/blob/main/docs/validate.rst) |
| 静态交互图 | [Cytoscape.js](https://github.com/cytoscape/cytoscape.js) + [cytoscape-dagre](https://github.com/cytoscape/cytoscape.js-dagre) | Cytoscape.js 同时提供浏览器图模型、交互渲染、事件、选择器和布局扩展；Dagre 适合 Flow/Stage 这类 DAG 和树状结构。[Cytoscape 布局与事件](https://js.cytoscape.org/index.html)、[Dagre 用途](https://github.com/cytoscape/cytoscape.js-dagre#description) | 两者均为 MIT（[Cytoscape LICENSE](https://github.com/cytoscape/cytoscape.js/blob/unstable/LICENSE)，[Dagre 仓库许可标识](https://github.com/cytoscape/cytoscape.js-dagre)）。扩展必须逐个核对许可证。 |
| 离线 HTML 构建 | [Vite](https://github.com/vitejs/vite) + [vite-plugin-singlefile](https://github.com/richardtallent/vite-plugin-singlefile) | Vite 管理前端构建；插件把 JS/CSS 内联到一个 `index.html`，官方 README 明确把无需服务器、双击可开的离线文档列为适用场景。[插件说明与限制](https://github.com/richardtallent/vite-plugin-singlefile/blob/main/README.md) | 两者均为 MIT（[Vite LICENSE](https://github.com/vitejs/vite/blob/main/packages/vite/LICENSE.md)，[插件仓库](https://github.com/richardtallent/vite-plugin-singlefile)）。被内联的所有前端依赖仍属于再分发，产物必须带第三方许可清单。 |

### Runtime Grounding 的最小增量

| 环节 | 默认模块 | 采用理由 | 许可证 / 边界 |
|---|---|---|---|
| 运行协议 | OpenTelemetry SDK + [GenAI Semantic Conventions](https://github.com/open-telemetry/semantic-conventions-genai) | OTLP 负责传输，GenAI conventions 负责 inference、embedding、retrieval、tool 等通用属性；独立仓库还提供版本化 schema URL。[GenAI spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md) | Apache-2.0。GenAI spans 当前仍标为 **Development**，必须锁定 schema URL/版本，并在 Adapter 中做版本迁移，不能直接把属性名当永久领域模型。 |
| 自动 instrumentation | [OpenTelemetry Python GenAI instrumentations](https://github.com/open-telemetry/opentelemetry-python-genai)；覆盖不足时用 [OpenInference](https://github.com/Arize-ai/openinference) Adapter | 官方 OTel 仓库正在承接 Python GenAI SDK/framework instrumentation；OpenInference 覆盖 OpenAI、Anthropic、LangChain、LlamaIndex、DSPy、MCP 等更多集成，且输出可发往任意 OTel 后端。[OpenInference 支持范围](https://github.com/Arize-ai/openinference#instrumentation) | 均为 Apache-2.0。OpenInference 有自己的语义约定，不能与 OTel `gen_ai.*` 假定为同一 Schema；在 `TraceSource` Adapter 中规范化。 |
| Trace / Prompt / Eval 后端 | [Langfuse OSS core](https://github.com/langfuse/langfuse) | 能接收 OTLP/HTTP，并提供 tracing、prompt management、datasets、experiments 和 evaluations；Codebase System Map 可通过 Observations API v2 和 Scores API 拉取证据。[OTel 接入](https://langfuse.com/docs/observability/get-started)、[数据 API](https://langfuse.com/docs/api-and-data-platform/overview) | Core 为 MIT，但仓库内 EE 目录另受企业许可；必须遵循根 [LICENSE 的目录边界](https://github.com/langfuse/langfuse/blob/main/LICENSE)。自托管部署并不轻：官方 compose 包含 web、worker、PostgreSQL、ClickHouse、Redis 和 MinIO，[compose 文件](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml)。因此它属于 Phase 2 的可选外部服务，不是 CLI 的硬依赖。 |

最小路径由此变成：

```text
Repository
  ├─ ast-grep adapter ──> syntax/prompt facts
  └─ Joern adapter ─────> symbols/calls/data-flow facts
                              │
                              v
                    Canonical Graph Builder
                       (NetworkX + rules)
                              │
                  JSON Schema validation
                              │
                    system-map.json
                              │
           Cytoscape.js + Vite single-file build
                              │
                    system-map.html

Optional runtime:
Application ──OTLP──> Langfuse ──API──> TraceSource adapter ──> Graph Builder
```

## 为什么是这套组合

### 1. ast-grep 替代“自写多语言 Prompt Scanner”

Prompt 与 LLM 调用没有跨框架统一静态语法，但它们通常落在有限的结构模式中：

- SDK 调用，例如 `client.chat.completions.create(...)`；
- framework 构造，例如 prompt template、chain、agent、tool decorator；
- 外部 prompt 文件加载，例如 `read_text(...)`、模板 loader；
- model/config 参数，例如 `model`、`temperature`、`tools`、structured output schema。

这些模式适合写成项目自有的 ast-grep YAML rule packs。ast-grep 的模式使用源码式 pattern 和 metavariable，而不是要求调用方处理各语言 AST；CLI 的 `--json=stream` 适合大仓库增量消费。[CLI 参考](https://ast-grep.github.io/reference/cli)、[JSON streaming](https://ast-grep.github.io/guide/tools/json)。

每条规则只输出候选事实，不直接断言 Flow/Stage：

```json
{
  "source": "ast-grep",
  "rule_id": "python.openai.chat-completion",
  "fact_type": "llm_call_candidate",
  "file": "src/writer.py",
  "range": {"start_line": 42, "end_line": 51},
  "captures": {"model": "MODEL", "messages": "MESSAGES"},
  "confidence": 0.85
}
```

这样增加一个 AI framework 主要是增加 rule pack，不需要修改核心图构建器。

Tree-sitter 本身仍是有价值的底层选择：它能为任意语言生成并增量更新 concrete syntax tree，[官方介绍](https://tree-sitter.github.io/)。但 MVP 不必再直接封装一层 Tree-sitter，因为 ast-grep 已经提供查询、规则、并行扫描和 JSON 输出。只有 ast-grep 未覆盖的自定义语言或嵌入式 DSL 才启用 `SyntaxExtractor` 的 Tree-sitter 实现。Tree-sitter core 是 MIT，[LICENSE](https://github.com/tree-sitter/tree-sitter/blob/master/LICENSE)；每个 grammar 是独立发行物，必须单独审计许可证。

### 2. Joern 负责“语义图”，但不能成为领域模型

Joern 的 Code Property Graph 是跨语言的有向、有标签、带属性多重图，节点覆盖 method、variable、control structure 等程序构造。[CPG 说明](https://docs.joern.io/code-property-graph/)。官方文档列出的语言成熟度并不一致：C/C++、Java 很高，JavaScript、Python 较高，Go/Kotlin/PHP 等较低，因此输出应保留 `analyzer`、`analyzer_version` 和 `confidence`。[支持语言表](https://docs.joern.io/)。

部署上也不应低估 Joern：官方安装要求 JDK，且大仓库需要显式调整 JVM heap；导入代码会再启动一个 JVM，可能同时消耗额外内存。[安装与内存说明](https://docs.joern.io/installation/)。因此建议：

- 以固定版本的 CLI/容器运行；
- 只导出我们需要的 method、type、call、source location 和 data-flow 子集；
- 将结果立即转换为自有 `implementation-facts.ndjson`；
- 当 Joern 不支持某语言或失败时，保留 ast-grep 的语法图并标记降级，不阻断整个文档构建。

### 3. 第一版不要部署图数据库

最终产物是静态 HTML，并非多人在线图查询服务。MVP 的图通常可以在内存中合并，用 NetworkX 完成：

- 重复节点合并；
- 悬空边、循环和不可达节点检测；
- Flow/Stage 的拓扑排序；
- 某节点所有 downstream descendants；
- 静态边与 runtime observed edge 的差异。

Canonical truth 应是经过 Schema 校验的 `system-map.json`，不是某个数据库文件。这个选择避免数据库迁移、服务进程、备份和许可证成为 CLI 的前置条件。

若未来出现数百仓库、在线多用户查询、跨版本保留等真实需求，再实现 `GraphStore`：

```python
class GraphStore(Protocol):
    def replace_snapshot(self, snapshot: SystemMap) -> None: ...
    def neighbors(self, node_id: str, direction: str) -> list[str]: ...
    def paths(self, source: str, target: str, max_depth: int) -> list[list[str]]: ...
```

这一接口不能暴露 Cypher、NetworkX object 或数据库内部 ID。

## Runtime 与 Eval：标准优先、平台可换

### OpenTelemetry 是边界，不是 Langfuse SDK

应用侧应优先发标准 OTel spans。Codebase System Map 自有字段放在独立 namespace，例如：

```text
codebase_map.flow.id
codebase_map.stage.id
codebase_map.prompt.id
codebase_map.prompt.version
codebase_map.artifact.input
codebase_map.artifact.output
```

LLM/provider/tool 的标准字段采用锁定版本的 OTel GenAI conventions。原因是官方 conventions 仍处在 Development，且 2026 年已经从通用 semantic-conventions 仓库迁入独立仓库；新的仓库明确提供自己的 schema URL。[迁移说明](https://github.com/open-telemetry/semantic-conventions/releases)、[新仓库 README](https://github.com/open-telemetry/semantic-conventions-genai)。

建议的数据边界：

```typescript
interface TraceSource {
  read(request: {
    repositoryRevision: string;
    from?: string;
    to?: string;
  }): AsyncIterable<NormalizedSpan>;
}
```

可分别实现 `LangfuseTraceSource`、`PhoenixTraceSource`、`OtlpFileTraceSource`。这样平台只提供证据，绝不拥有 Canonical Graph。

### Langfuse 何时值得引入

Langfuse 适合以下条件同时成立时引入：需要可视化调试真实 Trace、Prompt 版本管理、Dataset/Experiment/Eval，并愿意运维其完整数据栈。其官方资料声明核心 tracing、evaluation、prompt management、experiment、annotation 等能力采用 MIT 许可，而 SCIM、audit log、data retention 等企业模块需要商业许可。[官方开源说明](https://langfuse.com/handbook/chapters/open-source)。

Codebase System Map 应只使用稳定集成面：

- 写入：OTLP/HTTP；Langfuse 官方把 OTel endpoint 作为新 trace ingestion 的支持路径。[Public API](https://langfuse.com/docs/api-and-data-platform/features/public-api)
- 读取：Observations API v2、Scores API、Experiments API；不要读 Langfuse 的 PostgreSQL/ClickHouse 表。[Observations API v2](https://langfuse.com/docs/api-and-data-platform/features/observations-api)
- 版本：锁定服务端 major 与 API；Langfuse v4 已转为 observations-first，旧 ingestion API 正在淘汰。[兼容性说明](https://langfuse.com/docs/compatibility)

Prompt、completion、tool 参数可能包含个人数据、密钥或业务机密。默认不应采集正文；必要时在应用内或信任边界内的 Collector 先做 redaction。Langfuse 官方也建议敏感数据尽可能在离开应用前遮蔽，或在 Collector 使用 attributes/redaction/transform processors。[Masking 指南](https://langfuse.com/docs/observability/features/masking)。

## 输出层设计

### Cytoscape.js 只读 View Model

不要让前端直接理解完整领域 Schema。Renderer 先把 `system-map.json` 转成稳定的 `view-model.json`：

```json
{
  "elements": {
    "nodes": [{"data": {"id": "research.planner", "kind": "stage"}}],
    "edges": [{"data": {"id": "e1", "source": "research", "target": "research.planner", "kind": "contains"}}]
  },
  "detailsById": {},
  "searchIndex": []
}
```

Cytoscape.js 官方定义的是 graph theory model + optional renderer，可在 Node 或浏览器运行，[项目说明](https://github.com/cytoscape/cytoscape.js#description)。因此它适合承担选择、折叠、高亮邻域和 downstream impact，但不应反向写入领域数据。

对于主要为 DAG 的 Flow View 使用 cytoscape-dagre；超大 implementation graph 必须按需展开或分层加载，不能一次把所有 code entity 和 edge 画出来。

### 单文件 HTML 是发布模式，不是开发架构

开发和测试保持标准 Vite 工程；发布时才用 `vite-plugin-singlefile` 内联 JS/CSS 和已嵌入的 JSON。插件官方列出的限制包括不支持 History API 路由、多入口不适用、`public` 目录资源不保证内联、source map 在内联后无用。[插件 README](https://github.com/richardtallent/vite-plugin-singlefile/blob/main/README.md)。因此：

- 使用 hash route 或单页状态，不使用 history route；
- 将 `view-model.json` 作为 `<script type="application/json">` 注入 HTML，避免 `file://` fetch 差异；
- 图片和字体优先内联或使用系统字体；
- CI 同时产出 `system-map.html` 与 `THIRD_PARTY_LICENSES.txt`；
- 大仓库可额外提供目录式 build，单文件只是默认交付选项。

## 替代项与不采用项

| 模块 | 适用场景 | 不作为默认的原因 | 许可证 / 风险 |
|---|---|---|---|
| [Semgrep CE](https://github.com/semgrep/semgrep) | 团队已有 Semgrep 规则资产，或其语言 pattern 对目标框架更好用时，替换 ast-grep Adapter。官方 CE 可本地运行并输出 JSON/SARIF。[CE 说明](https://semgrep.dev/products/community-edition) | CE 的跨函数/跨文件分析能力有限；官方对比页将 CE 定位为单函数分析。[能力对比](https://semgrep.dev/products/semgrep-vs-ce/) | Engine 为 LGPL-2.1，[LICENSE](https://github.com/semgrep/semgrep/blob/develop/LICENSE)。官方维护的 community rules 自 2024 年采用限制 SaaS/竞争用途的 Semgrep Rules License；应使用本项目自写规则，不复制官方 rule registry。[规则许可变更](https://semgrep.dev/blog/2024/important-updates-to-semgrep-oss) |
| [Tree-sitter](https://github.com/tree-sitter/tree-sitter) direct API | 自定义语言、embedded DSL、需要增量 CST 时 | 自己维护所有查询、语言分发和结果规范化成本高；ast-grep 已封装大部分 MVP 需求 | Core MIT；grammar 逐个审计。 |
| [OpenInference](https://github.com/Arize-ai/openinference) | OTel 官方 instrumentation 尚未覆盖某 framework/provider；或选 Phoenix 时 | 它是补充 OTel 的 AI convention，不应同时把两套属性未经转换写入领域模型 | Apache-2.0，[LICENSE](https://github.com/Arize-ai/openinference/blob/main/LICENSE)。 |
| [Arize Phoenix](https://github.com/Arize-ai/phoenix) | 偏向 OpenInference、轻量本地 AI tracing/eval 体验，或内部自托管 | 官方功能覆盖 tracing、eval、datasets/experiments，但许可不是宽松开源；若将 Phoenix 的主要功能作为面向第三方的服务提供，ELv2 有明确限制 | Elastic License 2.0，[LICENSE](https://github.com/Arize-ai/phoenix/blob/main/LICENSE)；官方说明内部/自有云自托管允许，[self-host license](https://github.com/Arize-ai/phoenix/blob/main/docs/phoenix/self-hosting/license.mdx)。对外 SaaS 前需单独法务确认。 |
| [Kuzu](https://github.com/kuzudb/kuzu) | 已有离线系统锁定旧版本，且愿意自行维护 | 它原本非常契合 embedded property graph + Cypher，但官方仓库已于 2025-10-10 归档并只读；不应成为新项目核心依赖 | MIT；主要风险是维护、安全更新和扩展服务器生命周期，不是许可。 |
| [Neo4j Community Edition](https://github.com/neo4j/neo4j) | 以后需要独立图服务、Cypher 和运维成熟度时 | 对单仓库静态 build 太重；CE 自托管、社区支持且缺少部分企业能力。[Community Edition 对比](https://neo4j.com/product/community-edition/) | GPL-3.0，[官方 licensing](https://github.com/neo4j/neo4j#licensing)。若采用，作为用户单独部署的外部服务，通过独立 driver 连接；随产品分发前做 GPL 审查。 |
| [CodeQL CLI](https://github.com/github/codeql-cli-binaries) | 已购买 GitHub Code Security 且只在被许可环境内做增强分析 | CLI/engine 不是开源模块，不可作为通用、可再分发的默认分析器；查询库的 MIT 不会覆盖 CLI | [CLI 自定义 LICENSE](https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md)限制闭源代码分析、自动化使用、再分发和 hosted solution；默认排除。 |
| [Graphology](https://graphology.github.io/) | 如果整个 Builder 改为 TypeScript，可替换 NetworkX | Python 方案下会多引入一套图内存模型；浏览器已有 Cytoscape.js | MIT，[官方组织仓库](https://github.com/graphology/graphology)。它支持导入导出 JSON 和 DAG/遍历等标准库，[serialization](https://graphology.github.io/serialization.html)、[standard library](https://graphology.github.io/standard-library/)。 |
| [Ajv](https://github.com/ajv-validator/ajv) | 前端需要再次校验嵌入数据，或 Builder 使用 TypeScript | Python Builder 已由 `python-jsonschema` 校验；双重校验不是 MVP 必需 | MIT，[LICENSE](https://github.com/ajv-validator/ajv/blob/master/LICENSE)。 |
| [ELK.js](https://github.com/kieler/elkjs) | 复杂端口、分层数据流布局超出 Dagre 能力时 | MVP 的 Flow DAG 不需要它；包使用 `EPL-2.0 OR GPL-3.0-or-later`，合规和归档 notices 比 MIT Dagre 更复杂 | [package license](https://github.com/kieler/elkjs/blob/master/package.json)、[EPL-2.0 文本](https://github.com/kieler/elkjs/blob/master/LICENSE.md)。 |

## 关键集成 seam

核心包只依赖以下中立数据类型，不依赖任何工具 SDK：

```text
RepositorySource
  -> repository metadata + files + git revision

SyntaxExtractor
  -> SyntaxFact[]
  implementations: AstGrepExtractor, TreeSitterExtractor

CodeGraphExtractor
  -> CodeEntityFact[] + CodeRelationFact[]
  implementations: JoernExtractor, SyntaxOnlyFallback

TraceSource
  -> NormalizedSpan[] + EvalFact[]
  implementations: Langfuse, Phoenix, OTLP file

CanonicalGraphBuilder
  (facts + human metadata -> system-map.json)

GraphEngine
  -> validate / descendants / paths / SCC / topology
  implementation: NetworkX

DocumentRenderer
  (system-map.json -> self-contained HTML)
```

所有外部事实统一保留：

```json
{
  "origin": "static|runtime|human|inferred",
  "source_system": "ast-grep|joern|langfuse|phoenix|manual",
  "source_version": "...",
  "repository_revision": "...",
  "source_refs": [{"file": "...", "start_line": 1, "end_line": 4}],
  "confidence": 0.0,
  "observed_at": "..."
}
```

外部工具的 ID 只能放在 `external_refs`；Canonical node ID 必须由项目规则生成，避免更换分析器导致整份文档产生无意义 diff。

## 建议的交付顺序

### Iteration 1：静态纵向闭环

1. 定义 Draft 2020-12 `system-map.schema.json` 与 provenance 字段。
2. 建立 ast-grep rule pack，只覆盖一个目标仓库中的 Python/TypeScript AI SDK 与 prompt loader。
3. 用 Joern CLI 导出 method/call/location 子集；失败时允许 syntax-only。
4. 用 NetworkX 合并和验证，生成稳定排序的 `system-map.json`。
5. 用 Cytoscape.js + Dagre 完成 Flow View、详情抽屉、搜索和 downstream highlight。
6. 用 Vite single-file build 产出可双击打开的 `system-map.html`。

### Iteration 2：Runtime Grounding

1. 定义 `codebase_map.*` span 属性及内容采集默认关闭策略。
2. 选一个官方 OTel GenAI instrumentation 做端到端验证。
3. 独立部署 Langfuse OSS core，以 OTLP 写入、API 读取；不读取其数据库。
4. 把 observed stage order、tool call、model、latency、token usage 和 eval score 合入图，同时保留 static-vs-runtime 差异。

### Iteration 3：可替换性验证

不必同时维护多个后端，但应做两个 contract tests：

- `SyntaxExtractor`：同一 fixture 分别用 ast-grep 与 syntax fallback，输出满足同一 fact schema；
- `TraceSource`：用固定 OTLP fixture 模拟 Langfuse/Phoenix，归一化结果满足同一 span schema。

如果这两个测试成立，开源模块就是可替换组件，而不是新的供应商锁定。

## 许可证与部署检查清单

- 锁定每个 CLI、容器和 npm/Python 包版本，不在 CI 使用浮动 `latest`。
- 为 Tree-sitter grammars、Cytoscape extensions、Joern distribution 内第三方组件分别记录许可证。
- 静态 HTML 会实际再分发 Cytoscape.js、Dagre 等代码；在 HTML 的 About/License 面板或同目录 `THIRD_PARTY_LICENSES.txt` 保留声明。
- 若分发 Semgrep CE、Neo4j CE 或它们的修改版，先审查 LGPL/GPL 义务；默认使用用户自装或独立进程/服务也不能替代法律判断。
- Langfuse 只把 MIT core 计入开源依赖，明确排除或单列 EE 目录和商业功能。
- Phoenix 是 ELv2，不要称为 OSI-approved open source，也不要未经确认将其完整功能包装成第三方托管服务。
- CodeQL 查询库与 CodeQL CLI/engine 许可证不同；默认构建不得下载或再分发 CLI。
- Prompt、completion、tool arguments、retrieved documents 默认属于敏感数据；静态 HTML 发布前还要做内容分级和 redaction，而不只是依赖许可证审查。

## 最终建议

将原设计中的：

```text
Graphify + OpenTelemetry + Langfuse + Prompt Scanner
```

改成更具体且可替换的：

```text
ast-grep rules              # Prompt/LLM/Tool 与语法事实
      +
Joern adapter               # 跨语言调用/数据流事实，可降级
      +
NetworkX                    # 构建期合并、验证、影响分析
      +
JSON Schema 2020-12         # 长期数据契约
      +
Cytoscape.js + Dagre        # 人类可读交互图
      +
Vite single-file build      # 离线 HTML 交付

Phase 2 only:
OpenTelemetry GenAI + Langfuse adapter
```

这套组合把最难、最有产品价值的部分留给本项目：如何把“语法事实 + 调用关系 + 运行证据 + 人工语义”合并为可信的人类说明；解析、图算法、Tracing 存储和浏览器渲染则尽量复用成熟模块。
