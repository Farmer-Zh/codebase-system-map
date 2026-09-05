# Living AI System Map：以完整开源产品为基座的方案

> 调研快照：2026-09-04  
> 范围：仅引用候选项目的官方 GitHub、官方文档和许可证。许可证判断不是法律意见；落地前仍应锁定具体版本并做依赖许可证审查。

## 结论先行

可以，而且应该进一步减少自研。此前“若干底层库 + 自有 Compiler + 自有 Document Compiler + 自有 Renderer”的路线，虽然模块化，却仍然等于自行建设一个代码知识平台。现在已有更高层项目覆盖了仓库摄取、AST、关系图、GraphRAG、LLM Wiki、增量更新和文档导出，Living Map 不必再拥有这些通用能力。

最合理的新定位是：

> **Living Map 不再是独立平台，而是现有 Code Wiki 产品上的 AI-system domain pack。**

推荐顺序：

1. **默认推荐：以 [PorunC/CodeWiki](https://github.com/PorunC/CodeWiki) 为基座。**它已经覆盖本项目绝大多数端到端能力，MIT 许可，并直接支持交互式 standalone HTML。预计只需保留原完整设想约 **15%–25%** 的专有开发量。
2. **若能接受 AGPL 或购买商业许可：以 [Repowise](https://github.com/repowise-dev/repowise) 为基座。**它的代码图、execution flow、增量 Wiki、变化影响和运维成熟度更强，预计仅剩 **10%–20%** 自研；但其根许可证是 AGPL-3.0，嵌入闭源产品需商业授权。[官方商业许可说明](https://github.com/repowise-dev/repowise/blob/main/docs/business/COMMERCIAL.md)
3. **仅限非商业研究或先取得商业许可：以 [GitNexus](https://github.com/nxpatterns/gitnexus) 为基座。**它已能识别 execution processes 并生成 graph-grounded wiki，但当前采用 PolyForm Noncommercial 1.0.0，不是适合默认商用集成的开放源代码许可证。[LICENSE](https://github.com/nxpatterns/gitnexus/blob/main/LICENSE)

不建议把三者混搭。它们都在重复解决解析、图存储、检索、文档和 UI；并用只会重新引入 Adapter、同步、ID 对齐和双重缓存。应选择一个产品基座，直接接受其原生数据模型，把 `system-map.json` 降为可选导出格式，而不是再建一套 canonical core。

## 能力对比

符号说明：`✅` 已有端到端能力；`◐` 有相关能力但不完整；`❌` 不具备。表中“增量”指仓库变更后避免全量重新生成图和文档，而不只是缓存同一请求。

| 候选 | Repo ingestion | 代码关系图 | LLM 文档 | 人类输出 | 增量更新 | 扩展 AI Flow 等领域类型 | 离线 / 自托管 | 许可证 | 作为基座后的剩余自研 |
|---|---:|---:|---:|---|---:|---:|---:|---|---|
| **[PorunC/CodeWiki](https://github.com/PorunC/CodeWiki)** | ✅ 本地路径/Git URL | ✅ AST + 调用/继承/路由/配置 | ✅ GraphRAG Wiki + 引用校验 | ✅ Web UI；Obsidian Markdown ZIP；**standalone HTML** | ✅ 图与 Wiki 两层增量 | ◐ 有 capture specs、augmenters、metadata，但尚无 AI 专属类型 | ✅ SQLite、本地服务、Docker、Ollama | [MIT](https://github.com/PorunC/CodeWiki/blob/main/LICENSE) | **15%–25%** |
| **[Repowise](https://github.com/repowise-dev/repowise)** | ✅ 本地单仓/多仓 | ✅ 19 种语言、调用图、execution flows、跨仓 contracts | ✅ 结构 Wiki + 可选 LLM prose | ✅ Dashboard；Markdown/HTML/JSON/Structurizr；HTML 为多文件 | ✅ hooks/watch/webhook，按受影响页面更新 | ◐ 框架扩展结构成熟，但 AI 专属 ontology 仍需新增 | ✅ 本地、自托管、Ollama；air-gap 属商业计划边界 | [AGPL-3.0 或商业许可](https://github.com/repowise-dev/repowise/blob/main/docs/business/COMMERCIAL.md) | **10%–20%** |
| **[GitNexus](https://github.com/nxpatterns/gitnexus)** | ✅ 本地 repo/浏览器 ZIP | ✅ 多语言图、process trace、impact、tool map | ✅ graph-grounded wiki | ◐ Web UI + Wiki；未提供 standalone HTML 导出 | ◐ 可更新 stale index，但 README roadmap 仍把 changed-files-only indexing 列为进行中 | ◐ pipeline phase 可扩展但不是外部插件 API | ✅ CLI 无网络、浏览器 WASM、Docker | [PolyForm Noncommercial 1.0.0](https://github.com/nxpatterns/gitnexus/blob/main/LICENSE) | **10%–20%**，另有许可问题 |
| [DeepWiki-Open](https://github.com/AsyncFuncAI/deepwiki-open) | ✅ GitHub/GitLab/Bitbucket，私库 | ◐ RAG 文本理解 + LLM Mermaid，不是确定性调用图 | ✅ 完整 Wiki / Ask / Deep Research | ✅ Web UI；Markdown/JSON 导出 | ❌ 未见代码图与页面级增量协议 | ◐ 主要靠 prompt/页面生成定制 | ✅ Docker、本地 Ollama | [MIT](https://github.com/AsyncFuncAI/deepwiki-open/blob/main/LICENSE) | **35%–50%** |
| [RepoAgent](https://github.com/OpenBMB/RepoAgent) | ✅ 本地 Git repo | ◐ Python AST、对象间调用 | ✅ 对象级 Markdown | ✅ Markdown + GitBook 展示 | ✅ Git diff + pre-commit 文档替换 | ◐ prompt 可改，但当前只支持 Python | ✅ CLI；当前依赖 OpenAI-compatible API | [Apache-2.0](https://github.com/OpenBMB/RepoAgent/blob/main/LICENSE) | **45%–60%** |
| [Potpie](https://github.com/potpie-ai/potpie) | ✅ repo + GitHub/SDLC 来源 | ✅ living context graph | ❌ 产品重点是 agent context，不是发布文档 | ◐ 本地图浏览器 | ◐ context 更新存在，文档生命周期没有 | ◐ graph command/proposal 可扩展 | ✅ CLI daemon + local UI | [Apache-2.0](https://github.com/potpie-ai/potpie/blob/main/LICENSE) | **40%–55%** |
| [GitDiagram](https://github.com/ahmedkhaleel2004/gitdiagram) | ◐ GitHub API，只读取默认分支 tree + README | ❌ LLM 架构草图，不是代码关系图 | ◐ 一段解释 + 图 | ◐ Mermaid/PNG | ❌ | ❌ | ◐ 可本地开发/Docker，但正式架构依赖 R2、Redis、Vercel | [MIT](https://github.com/ahmedkhaleel2004/gitdiagram/blob/main/LICENSE) | **60%+** |
| [Aider repo map](https://aider.chat/docs/repomap.html) | ✅ 本地 Git repo | ◐ 关键符号 + 文件依赖排名 | ❌ 是给 LLM 的压缩上下文，不是文档生成器 | ❌ | ◐ 会随会话/仓库刷新 map | ◐ 需改 Aider 内部 | ✅ 本地 CLI | [Apache-2.0](https://github.com/Aider-AI/aider/blob/main/LICENSE.txt) | **60%+** |
| [Doxygen](https://www.doxygen.nl/manual/features.html) / Sphinx / MkDocs Material | ✅ 源码或 Markdown | ◐ Doxygen 有 include/call/caller/class graph | ❌ | ✅ 成熟静态 HTML；MkDocs Material 支持离线目录 | ◐ 构建工具级增量 | ◐ 适合主题/插件，不理解 AI 运行语义 | ✅ | 各项目许可证 | **它们是输出层，不是端到端基座** |

表中 CodeWiki 的能力依据其官方 README 和设计文档：它支持 Python、TypeScript/JavaScript、Java、Go、Rust、C/C++、C#，建立 deterministic imports/definitions/calls/routes/inheritance/config edges，并生成带源码引用、图表、翻译和增量更新的 Wiki。[README](https://github.com/PorunC/CodeWiki#highlights) [Usage Guide](https://github.com/PorunC/CodeWiki/blob/main/docs/usage.md#current-scope)

## 方案 A：PorunC/CodeWiki + Living Map AI domain pack（默认推荐）

### 为什么它最贴近目标

CodeWiki 自己的产品定义已经几乎等于本项目的通用部分：本地目录或 Git URL 经 RepoScanner、AST/tree-sitter、Code Graph、GraphRAG 后，生成可追溯源码的 Wiki，并在 React 前端提供 graph、wiki、ask 和 export。[官方设计的端到端流程](https://github.com/PorunC/CodeWiki/blob/main/docs/design.md#2-%E5%BD%93%E5%89%8D%E5%AE%9E%E7%8E%B0%E6%A6%82%E8%A7%88)

它已经实现了此前规划中准备自行开发的绝大多数模块：

- Repo 扫描、本地路径和 Git URL、ignore、Git revision；
- 九种语言的 tree-sitter AST 和内容 hash 缓存；
- file/symbol/import/call/inheritance/route/config 图；
- 边的 reason、confidence、inferred 和 provenance；
- 社区发现、GraphRAG、FTS 和可选向量检索；
- LiteLLM 路由、缓存、失败记录；
- Wiki catalog/page/translation、源码引用白名单和 Mermaid 校验；
- full/incremental analysis、受影响页面标 stale、按页更新；
- FastAPI、CLI、MCP、React 图浏览器；
- 浏览器侧的 interactive standalone HTML 和 Obsidian ZIP。

这些均可在官方 [Design Notes](https://github.com/PorunC/CodeWiki/blob/main/docs/design.md) 与 [Usage Guide](https://github.com/PorunC/CodeWiki/blob/main/docs/usage.md) 中核对。尤其重要的是，独立 HTML 已是现成功能，不需要再引入 Vite single-file 插件或自建 Renderer；导出在浏览器内从已加载 Wiki 数据完成，不依赖后台 export API。[Wiki Export](https://github.com/PorunC/CodeWiki/blob/main/docs/usage.md#wiki-export)

### Living Map 只保留什么

建议不再创建新的 artifact pipeline、plugin protocol、graph store 或 document renderer，只维护一个小型 `living-map-ai-pack`：

1. **AI framework recognizers**：在 CodeWiki 的 `capture_specs` / `augmenters` 扩展点上识别 Prompt、LLM Call、Tool、Retriever、Agent、Graph Node。官方 AST 层本来就以通用 `AstSymbol.metadata` 承载增强信息，并将语言增强器与 capture query 分开。[AST Parser 设计](https://github.com/PorunC/CodeWiki/blob/main/docs/design.md#53-ast-parser)
2. **AI semantic tags，而非新图内核**：MVP 先把 `ai_kind=prompt|tool|model_call|artifact`、framework、model expression、source range 放入现有节点 metadata；Flow/Stage 作为从 endpoint/entry point 到 model/tool call 的命名路径或 Wiki 页面元数据。只有 UI 确实需要独立筛选时，才把这些提升为一级 node types。
3. **Living Map Wiki profile**：替换/补充 catalog 和 page prompt，固定生成 `System Overview`、`Flows`、`Stages`、`Prompts & Tools`、`Artifacts`、`Impact` 页面。CodeWiki 已把 catalog、page、validator、diagram、source rendering 分成清晰子模块，无需另建 Document Compiler。[Wiki 子系统设计](https://github.com/PorunC/CodeWiki/blob/main/docs/design.md#9-wiki-%E7%94%9F%E6%88%90%E8%AE%BE%E8%AE%A1)
4. **少量 UI 词汇和过滤器**：给上述 metadata 增加颜色、图例、过滤条件和详情字段；继续复用现有图浏览、Wiki、search、impact 和 standalone HTML export。
5. **可选兼容导出**：若外部集成确实需要 `system-map.json`，由 CodeWiki graph/query API 生成一个只读 export；它不再是内部唯一真相。

### 预计自研量

相对于此前完整设计，约保留 **15%–25%**：

- 8%–12%：首批 3–5 个 AI framework recognizers；
- 3%–5%：Flow/Stage 路径归纳和命名策略；
- 2%–4%：Wiki profile 与校验规则；
- 2%–4%：UI 标签/筛选和可选 JSON export。

其余约 75%–85% 直接继承上游。这个比例是工程范围估算，不是已完成的 LOC 测量。最关键的取舍是：**接受 CodeWiki 的数据库、模型和 UI，不再抽象一套可替换的 Canonical Graph。**

### 风险

- 项目仍较年轻。GitHub 当前显示约 181 个 commits、158 stars，官方 changelog 最新稳定记录为 2026-06 的 `0.6.5`；在正式 fork 前应做一次 fixture bake-off 和依赖审计。[仓库](https://github.com/PorunC/CodeWiki) [Changelog](https://github.com/PorunC/CodeWiki/blob/main/docs/changelog.md)
- 当前一级节点类型只有 repository/directory/file/config/module/class/interface/schema/function/method/endpoint，AI 类型尚未内建。[现有图 Schema](https://github.com/PorunC/CodeWiki/blob/main/docs/design.md#61-%E8%8A%82%E7%82%B9%E7%B1%BB%E5%9E%8B)
- 若长期维护 fork，应尽量把改动放在新增 augmenter、prompt profile 和 UI registry，避免修改 scanner、GraphRAG、store 和 export 主干，以便持续合并上游。

## 方案 B：Repowise + AI framework extension（能力最强，受许可证约束）

Repowise 已是更成熟、更宽的“代码库知识产品”：它索引代码图、Git history、docs、decisions 和 code health；代码图包含 19 种 AST 语言、confidence-stamped call resolution、communities、cycles 和 execution flows，文档按模块/文件增量重建。[官方 README 的 intelligence layers](https://github.com/repowise-dev/repowise#what-the-index-builds)

它还自带：

- 单仓和多仓 workspace ingestion；
- entry-point execution flow 和跨仓 HTTP/gRPC/event contracts；
- 结构 Wiki（无需模型）及可选 LLM prose；
- dashboard 内 Docs、Graph、C4、Knowledge Map、execution flows、blast radius；
- post-commit hooks、watcher、webhooks/polling 增量维护；
- Markdown、HTML、JSON 和 Structurizr DSL 导出。HTML 当前是一页一文件，不是 single-file HTML。[CLI export](https://github.com/repowise-dev/repowise/blob/main/packages/cli/README.md#repowise-export)

Living Map 只需新增 AI framework dynamic hints、Prompt/Tool/Artifact 标注、AI 专用 Wiki 模板，并可选增加单文件打包。若接受 Repowise 的页面结构和多文件 HTML，剩余开发约 **10%–20%**，可能比方案 A 更少。

但许可证是决定性边界：仓库根部标示 AGPL-3.0；官方说明内部使用开放版可行，但把 Repowise 嵌入自有产品且不愿承担 AGPL 义务时需要商业许可。[根仓库许可标识](https://github.com/repowise-dev/repowise) [Commercial Offering](https://github.com/repowise-dev/repowise/blob/main/docs/business/COMMERCIAL.md#7-licensing--pricing) 因此：

- Living Map 若明确保持 AGPL 开源，可直接 fork；
- 若计划闭源、SaaS 或商业再分发，应先谈商业授权，再把它定为技术基座；
- 不要因为 `packages/cli` README 曾显示 Apache-2.0 就忽略根仓库当前的 AGPL 条款，锁定版本后应逐包审查。

## 方案 C：GitNexus + Wiki 主题（非商业/获授权时的最小实现）

GitNexus 在结构理解方面离 AI System Map 很近。官方管线会抽取函数/类/方法/接口，解析 imports、calls、heritage、DI，做 Leiden communities，并从 entry point 沿 call chain 形成 Process 节点和 `STEP_IN_PROCESS` 边。[How It Works](https://github.com/nxpatterns/gitnexus#how-it-works) [Pipeline Architecture](https://github.com/nxpatterns/gitnexus/blob/main/ARCHITECTURE.md#pipeline-dag)

其现成能力还包括：

- `processes` 资源直接给出 execution flows；
- `tool_map` 已能定位 MCP/RPC tool definition 和 handler；
- `impact`、`detect_changes`、`trace` 覆盖变更影响；
- `gitnexus wiki` 从图中用 LLM 分组模块、生成 overview 和逐模块页面；
- CLI 图索引完全本地，Web UI 可纯浏览器 WASM 运行，并提供 Docker 部署。[README](https://github.com/nxpatterns/gitnexus)

因此只需要补 Prompt/Artifact 检测、把 Process 映射为 Flow/Stage、Wiki 模板和静态 HTML export，开发约 **10%–20%**。不过存在两个硬约束：

1. 当前许可证是 **PolyForm Noncommercial 1.0.0**，只允许许可定义下的非商业目的；README 也明确写明 OSS 版本商业使用需要 proper licensing。[LICENSE](https://github.com/nxpatterns/gitnexus/blob/main/LICENSE) [Enterprise section](https://github.com/nxpatterns/gitnexus#enterprise)
2. `analyze` 可以更新 stale index，但官方 roadmap 仍把真正的 changed-files-only incremental indexing 列为进行中，不能把现状等同于成熟的增量图管线。[Roadmap](https://github.com/nxpatterns/gitnexus#roadmap)

所以它适合研究验证，或在拿到商业许可后直接采用；不应作为一个希望宽松开源或自由商用的默认依赖。

## 为什么其他候选不应成为主基座

### DeepWiki-Open

DeepWiki-Open 已有完整 Wiki UX、RAG、Ask/Deep Research、多模型和 Mermaid，并支持 GitHub/GitLab/Bitbucket 及私库。[官方 README](https://github.com/AsyncFuncAI/deepwiki-open/blob/main/README.zh.md) 它也有 `/export/wiki` 的 Markdown/JSON 导出。[API 文档](https://github.com/AsyncFuncAI/deepwiki-open/blob/main/README.zh-tw.md#-api-%E7%AB%AF%E9%BB%9E)

但其核心知识层是 repository files + embeddings/RAG，由 LLM 生成结构和图，不是可查询、带 provenance/confidence 的确定性代码关系图。要达到 Living Map 的可信 Flow/Stage/Impact，仍要另接代码图并重做数据融合，结果又回到上一版的大量 Adapter/Compiler 工作。因此它适合“快速得到漂亮 Wiki”，不适合本项目强调的可追溯系统地图。

### RepoAgent

RepoAgent 直接解决 repository-level documentation，支持 Git diff 检测、AST 对象结构、双向调用、增量替换 Markdown、pre-commit 自动维护和 GitBook 展示。[官方 README](https://github.com/OpenBMB/RepoAgent#-features) 但同一 README 仍说明当前 hook 只支持 Python，并把多语言和本地模型列为 Future Work。[限制与 Future Work](https://github.com/OpenBMB/RepoAgent#-future-work) 它的文档粒度偏文件/对象，补 AI domain graph、跨语言、交互式 flow UI 的工作仍较多。

### Potpie

Potpie 已把 repo、source history、decisions 和 engineering workflow 组织成 living context graph，并提供本地 graph explorer、CLI、agent skills 和多种 SDLC source integration。[官方 README](https://github.com/potpie-ai/potpie) 但它当前的产品输出是为 agent 提供 context/search/resolve，而不是构建、版本化和导出给人阅读的 Wiki。选择它仍需自行实现文档生成、引用校验、页面生命周期和发布产物，因此更适合作为 agent context platform，而非本项目底座。

### GitDiagram

GitDiagram 的输入事实只有 GitHub 默认分支的 recursive tree 和 README，随后由两个模型阶段生成 explanation 和 graph AST；输出是 Mermaid source 或 PNG。[官方生成流程](https://github.com/ahmedkhaleel2004/gitdiagram#how-generation-works) 它很适合快速架构草图，但不读取完整代码来构建调用/数据关系，也没有增量文档生命周期，不能承担 Living Map 的事实层。

### Aider repo map

Aider repo map 会用 tree-sitter 找重要符号，并按文件依赖图做 graph ranking，以给 LLM 一个有限 token budget 内的代码上下文。[官方 Repo Map 文档](https://aider.chat/docs/repomap.html) 它是优秀的检索/上下文组件，但不是持久代码图、Wiki generator 或人类文档系统；把它升级为产品基座反而会写更多代码。

### Doxygen / Sphinx / MkDocs Material

Doxygen 可从未注释源码生成交叉引用 HTML，并借助 Graphviz 输出 include、class、call 和 caller graphs。[Features](https://www.doxygen.nl/manual/features.html) [Graphs](https://www.doxygen.nl/manual/diagrams.html) 但它没有 LLM semantic synthesis，也不了解 AI Flow/Prompt/Tool/Artifact。

Sphinx/MkDocs Material 是成熟发布层；Material 能把 Markdown 构建成可搜索静态站点，并用 offline plugin 让目录直接从 `file://` 打开。[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) [Offline plugin](https://squidfunk.github.io/mkdocs-material/plugins/offline/) 它们适合渲染已经生成的 Markdown，而不能代替 repository understanding。采用 CodeWiki 时甚至不需要额外引入它们，因为 CodeWiki 已有 standalone interactive HTML export。

## 建议砍掉的自研设计

若选择方案 A，下面这些此前规划的模块全部删除：

| 原计划自研 | 改为 |
|---|---|
| `RepositorySnapshot`、repo scanner | CodeWiki `RepoScanner` |
| ast-grep/Joern adapters | CodeWiki tree-sitter capture specs + augmenters |
| `EvidenceBundle` 和通用证据协议 | CodeWiki graph node/edge metadata + source refs |
| `Canonical Graph Builder` | CodeWiki `GraphBuilder`、community 与 provenance |
| `ArtifactStore` / cache | SQLite/PostgreSQL store、AST cache、LLM cache |
| GraphRAG / retrieval | CodeWiki GraphRAGRetriever |
| `Document Compiler` | CodeWiki Wiki catalog/page orchestration |
| 引用和 Mermaid validator | CodeWiki `PageResponseValidator`、diagram pipeline |
| 前端图 UI | CodeWiki React + XYFlow/ELK |
| HTML renderer / single-file bundler | CodeWiki browser-side standalone HTML export |
| CLI / HTTP / MCP | CodeWiki 已有 interfaces |
| Schema migration system | 沿用 CodeWiki DB migrations；`system-map.json` 仅作派生 export |

新的边界只剩：

```text
PorunC/CodeWiki upstream
  + living-map-ai recognizers
      Prompt / Model Call / Tool / Retriever / Agent / Artifact candidates
  + living-map flow derivation
      Entry point -> ordered code path -> named Flow/Stage
  + living-map wiki profile
      固定面向人类的页面结构与置信度措辞
  + small UI registry
      AI 类型图例、筛选和详情字段
```

## 最小验证计划

不要先 fork 后大改。用 5–7 个工作日做一个可放弃的 bake-off：

1. 选一个真实的 Python 或 TypeScript AI 仓库，人工标出 2 个 Flow、5–8 个 Stage、3 个 Prompt、2 个 Tool、2 个 Artifact。
2. 原样运行 PorunC/CodeWiki：`repos add` → `analyze` → `wiki catalog/pages` → standalone HTML export，验证安装、性能、引用和离线查看。[官方命令](https://github.com/PorunC/CodeWiki#common-commands)
3. 只写一个 framework augmenter，把 Prompt、LLM Call 和 Tool 写进现有 metadata；不改数据库 schema。
4. 写一个 Flow page profile，让 LLM 只使用 graph paths 和 allowed source refs 生成上述 Flow/Stage 文档。
5. 修改一处 Prompt 和一处 Tool call，运行 `codewiki update`，确认图和相关页面按预期变 stale/重建。[增量命令](https://github.com/PorunC/CodeWiki/blob/main/docs/usage.md#cli)
6. 导出 standalone HTML，请一位不了解仓库的人回答“系统有哪些 Flow、每步用什么 Prompt/Tool、改这里影响哪里”。

通过条件：人工标注的关键实体召回率达到约 80%，所有结论能回到源码范围，修改后只重建受影响页面，HTML 可离线打开。若失败，再用同一 fixture 对 Repowise 做第二轮；不要回退到自研通用平台，除非两个完整产品都在同一关键能力上失败。

## 最终建议

采用：

```text
PorunC/CodeWiki (MIT, upstream product)
        +
Living Map AI domain pack (our differentiator)
        =
Repository -> source-grounded AI system wiki -> standalone HTML
```

这条路线比此前方案少掉的不是几个库，而是整个平台层：repo ingestion、AST、图构建、图存储、GraphRAG、LLM orchestration、增量更新、引用验证、API、CLI、MCP、图 UI 和 HTML export 都由一个完整上游承担。

本项目真正值得写的代码只剩一个问题：

> **如何在已有代码知识图中可靠识别 AI-specific semantics，并让已有 Wiki 以 Flow / Stage / Prompt / Tool / Artifact 的语言讲清楚它。**

如果未来发现 CodeWiki 的边界确实无法承载某项需求，再用一次具体失败来决定是否抽出独立模块；不应在尚未验证前预先重建它已经拥有的基础设施。
