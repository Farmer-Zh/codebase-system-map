# RepoAtlas：团队共享的系统行为与实现地图

## 1. 目标

对于 LLM 驱动的 AI 产品，团队真正需要同步的不是单纯的代码、Prompt
列表或传统架构图，而是：

> **当前软件如何运行、哪些 Prompt/Pipeline/Tool
> 共同决定结果、它们对应哪部分代码，以及修改后可能影响什么。**

最终交付物是一份团队内部可分享、可搜索、可交互、随代码持续更新的静态
HTML。HTML 首页以系统运行图为主体，节点可逐层展开到
Prompt、输入输出、Tool、实现代码、Eval 和版本变化。

核心问题：

-   当前有哪些主要 AI Flow？
-   每个 Flow 经过哪些 Stage？
-   Stage 的输入和输出是什么？
-   哪些 Prompt、Tool、Context、Model Config 参与其中？
-   多个 Prompt 如何共同形成最终结果？
-   没有直接用户可见结果的 Prompt 产生了什么内部 Artifact/Decision？
-   Stage/Prompt 对应哪部分代码？
-   修改一个 Prompt、Pipeline Stage 或共享组件后会影响什么？
-   当前版本相较上一版本发生了什么语义变化？

------------------------------------------------------------------------

## 2. 核心原则

### 2.1 首页展示运行图，而不是代码图

``` text
AI Product
   ├── Chat Flow
   ├── Search Flow
   └── Research Flow
          ↓
       Planner
          ↓
        Search
          ↓
   Evidence Selection
          ↓
        Writer
          ↓
   Citation Validation
```

继续下钻：

``` text
Flow
 ↓
Stage
 ↓
Prompt / Tool / Artifact
 ↓
Implementation
 ↓
Function / Class / File
```

非核心研发、产品和业务人员停留在上层；研发可以继续进入实现层。

### 2.2 Prompt 不是唯一中心

最终行为更接近：

``` text
Effective Behavior
=
Prompt
× Pipeline
× Context Construction
× Tooling
× Model Config
× Execution Order
× Post-processing
```

因此 Prompt 是 Execution Graph 中的重要节点，而不是唯一中心。

### 2.3 不强制 Prompt 与可见 Behavior 一一对应

例如：

``` text
query_classifier_prompt
        ↓
Classifier Stage
        ↓
ClassificationResult
        ↓
Router
        ↓
Research Flow
```

Classifier 没有直接用户可见输出，但仍是系统行为的重要决定因素。

### 2.4 静态结构 + Runtime Evidence

静态分析回答"系统可能如何执行"，Runtime Trace 回答"系统实际如何执行"。

最终应融合成 **Canonical Execution Graph**。

### 2.5 HTML 是 Build Artifact

团队不直接编辑 HTML：

``` text
Code + Prompts + Traces + Metadata
              ↓
         Graph Builder
              ↓
       system-map.json
              ↓
         HTML Renderer
              ↓
       system-map.html
```

------------------------------------------------------------------------

## 3. 三层模型

``` text
┌──────────────────────────────┐
│ Product / System View        │
│ Flow / Description / Effect  │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ AI Execution Graph           │
│ Stage / Prompt / Tool        │
│ Artifact / Context / Model   │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Implementation Graph         │
│ Function / Class / File      │
│ Dependency                   │
└──────────────────────────────┘
```

第一层负责团队理解；第二层是整个系统的核心；第三层负责工程下钻和代码影响分析。

------------------------------------------------------------------------

## 4. 核心节点

### Flow

完整或相对完整的 AI 工作流，例如 Chat、Search、Deep Research、Report
Generation。

``` yaml
id: research
type: flow
name: Deep Research
description: 对复杂问题进行规划、搜索、证据整理和综合
owners: [ai-team]
```

### Stage

Execution Graph 的核心节点，例如 Intent Router、Planner、Context
Builder、Search、Evidence Selector、Writer。

``` yaml
id: research.planner
type: stage
name: Research Planner
purpose: 将用户问题拆解为可执行研究计划
inputs: [user_request, conversation_context]
outputs: [research_plan]
implementation:
  - src/research/planner.py
```

### Prompt

Prompt 应成为版本化的一等资产：

``` yaml
id: research_planner
type: prompt
version: 12
purpose: 控制任务拆解与搜索计划生成
used_by: [research.planner]
source: prompts/research/planner.md
```

建议记录 stable
ID、version、purpose、owner、source、used-by、inputs、expected
output、last changed、related eval。

### Tool

例如 Web Search、Database Query、Internal API、Code Search。

### Artifact

Artifact 非常关键，例如：

-   UserRequest
-   ClassificationResult
-   ResearchPlan
-   SearchResults
-   EvidenceSet
-   DraftAnswer
-   FinalAnswer

它解决"Prompt 没有直接可见 Behavior"的建模问题：

``` text
Prompt → Stage → Artifact → Stage → Artifact → Final Output
```

### Code Entity

File、Function、Class、Module 等，由静态代码分析提供。默认不展示在
System View。

### Eval

从 schema 第一版就预留：

``` yaml
id: planner_coverage
type: eval
measures: research.planner
metric: plan_coverage
```

------------------------------------------------------------------------

## 5. 关键关系

建议使用明确关系，而不是泛化的 `related_to`：

``` text
Flow     --contains--------> Stage
Stage    --uses------------> Prompt
Stage    --uses------------> Tool
Stage    --consumes--------> Artifact
Stage    --produces--------> Artifact
Stage    --implemented_by--> Code Entity
Prompt   --loaded_by-------> Code Entity
Prompt   --contributes_to--> Stage / Effect
Artifact --feeds-----------> Stage
Eval     --measures--------> Stage / Prompt / Flow
Stage    --precedes--------> Stage
```

对于 AI 行为，优先使用 `contributes_to`，避免轻易宣称某个 Prompt 单独
`causes` 某个行为。

------------------------------------------------------------------------

## 6. 推荐总体架构

``` text
                         Git Repository
                              │
              ┌───────────────┼────────────────┐
              ↓               ↓                ↓
          Graphify       Prompt Scanner   Instrumentation
              │               │                │
              │               │          OpenTelemetry
              │               │                ↓
              │               │             Langfuse
              │               │        Trace / Prompt / Eval
              └───────────────┼────────────────┘
                              ↓
                       Graph Builder
                              │
                    ┌─────────┴─────────┐
                    ↓                   ↓
             system-map.json      change-set.json
                    │
                    ↓
                HTML Renderer
                    │
                    ↓
              system-map.html
                    │
                    ↓
           Internal Static Hosting
```

------------------------------------------------------------------------

## 7. 技术选型

### Graphify：Implementation Graph

负责 AST、Function/Class/Module 关系、调用/依赖、Prompt
的代码使用位置以及底层 impact analysis。

Graphify 是数据源，不直接作为最终团队界面。

### OpenTelemetry：Execution Graph 基础协议

在关键 Stage 加 instrumentation：

``` python
with tracer.start_as_current_span("research.planner"):
    ...
```

建议 metadata：

``` text
flow.id = research
stage.id = research.planner
prompt.id = research_planner
prompt.version = 12
input.artifact = UserRequest
output.artifact = ResearchPlan
```

这样 runtime 本身开始"自描述"，同时避免被某个 observability 产品锁定。

### Langfuse：Prompt + Trace + Eval

第一选择，用于：

-   Prompt Registry / Version
-   LLM Generation Trace
-   Nested Span / Tool Call
-   Dataset / Experiment / Eval

它主要提供"系统实际上如何运行"的证据。

### Phoenix / Braintrust：备选

不建议第一阶段同时引入。Langfuse 不满足要求时，再分别评估偏开源自托管的
Phoenix 或偏实验/Eval 工作流的 Braintrust。

### Cytoscape.js：最终 HTML 图层

负责 Interactive Graph、Expand/Collapse、Filter、Path、Neighborhood
Highlight、Impact Highlight。

### Mermaid：局部辅助

适合节点详情中的小型流程图，不建议作为主交互图。

------------------------------------------------------------------------

## 8. system-map.json 是核心长期资产

真正需要长期掌握的是 vendor-neutral 的 `system-map.json`，而不是任何单个
SaaS。

``` json
{
  "nodes": [
    {"id": "research", "type": "flow", "name": "Deep Research"},
    {"id": "research.planner", "type": "stage", "name": "Research Planner"},
    {"id": "research_planner", "type": "prompt", "version": 12},
    {"id": "research_plan", "type": "artifact", "name": "ResearchPlan"}
  ],
  "edges": [
    {"from": "research", "to": "research.planner", "type": "contains"},
    {"from": "research.planner", "to": "research_planner", "type": "uses"},
    {"from": "research.planner", "to": "research_plan", "type": "produces"}
  ]
}
```

Graphify、Langfuse、OpenTelemetry、Git 和人工 metadata
都只是它的数据源。

------------------------------------------------------------------------

## 9. HTML 产品设计

### System View

默认只显示：

``` text
Flow → Stage → Prompt / Tool / Artifact
```

### Engineering View

点击 `Show Implementation` 后：

``` text
Stage → Function → Class → Module
```

### Node Detail Drawer

Stage 节点建议展示：

``` text
Research Planner

PURPOSE
将复杂问题拆解成研究计划

INPUTS
UserRequest
ConversationContext

OUTPUT
ResearchPlan

PROMPTS
research_planner_v12
planner_constraints_v4

TOOLS
...

MODEL
...

OBSERVABLE EFFECT
间接影响搜索范围、覆盖度和成本

IMPLEMENTATION
src/research/planner.py

DOWNSTREAM
Search Orchestrator

EVALS
plan_coverage
unnecessary_search_rate
```

Prompt 节点展示完整
Prompt、版本、使用位置、输入输出、加载代码、最近变更和关联 Eval。

### Impact Highlight

点击共享节点后高亮 downstream：

``` text
             Context Builder
              /     |      \
             ↓      ↓       ↓
          Search Research   Chat
```

这能快速表达 blast radius。

### Search / Ask

第一阶段提供结构化搜索；第二阶段加入 "Ask this system"，例如：

-   Research 是怎么工作的？
-   哪些 Flow 使用 research_planner？
-   Citation 在哪一步产生？
-   修改 Context Builder 会影响什么？

------------------------------------------------------------------------

## 10. 版本与 Semantic Diff

顶部提供版本选择：

``` text
main @ abc172
Release v2.4
Release v2.3
2026-09-01
```

支持 `Compare with previous`。

### Prompt Semantic Diff

``` text
writer_prompt v18 → v19

Semantic Change
当简洁与事实完整性冲突时，明确优先事实完整性。

Potential Effects
- 回答长度可能增加
- 信息覆盖率可能提高

Affected Flows
- Research
- Search

Related Evals
- completeness
- verbosity
- groundedness
```

### Pipeline Diff

``` text
Context Builder

Before
Top 20 chunks

After
Top 40 chunks + reranking

Potentially Affected
- Research Writer
- Search Answer
- Summary Generator
```

团队讨论的重点因此从"最近改了哪些代码"转变为"系统有效行为边界发生了什么变化"。

------------------------------------------------------------------------

## 11. 持续更新机制

不要每次 commit 都让 LLM 重写整个文档。

### Deterministic Update

``` text
Git Diff
 ↓
Graphify Incremental Scan
 ↓
Prompt Scanner
 ↓
Static Graph Update
```

### Semantic Update

``` text
planner.py changed
 ↓
research.planner marked dirty
 ↓
Find affected semantic nodes
 ↓
Regenerate only affected annotations
```

这样可以避免少量代码变化导致大量无意义文档 diff。

------------------------------------------------------------------------

## 12. CI/CD

``` text
git push
   ↓
Detect changed files
   ↓
Graphify incremental scan
   ↓
Prompt discovery / version detection
   ↓
Collect OTel/Langfuse metadata
   ↓
Update affected Execution Graph
   ↓
Semantic impact analysis
   ↓
Build system-map.json
   ↓
Generate system-map.html
   ↓
Publish internal site
```

建议 repo：

``` text
repo/
├── src/
├── prompts/
├── ai-map/
│   ├── flows.yaml
│   ├── stages.yaml
│   └── annotations.yaml
├── graphify-out/
│   └── graph.json
├── generated/
│   ├── system-map.json
│   ├── change-set.json
│   └── system-map.html
└── scripts/
    └── build-system-map.*
```

------------------------------------------------------------------------

## 13. 自动与人工信息边界

### 尽量自动生成

-   Code Entity
-   Call/Import/Dependency
-   Prompt source/version
-   Prompt 被哪些代码加载
-   Runtime Stage 顺序
-   Tool Call
-   Model invocation
-   Input/output Artifact 类型
-   Git change
-   Runtime frequency/latency
-   Eval result

### 少量人工确认

-   Flow 的业务/系统名称
-   Stage 的 purpose
-   哪些 Stage 值得作为团队沟通边界
-   Observable Effect 描述
-   Owner
-   关键风险解释

原则：

> **AI generated + human confirmed，而不是 human maintained。**

------------------------------------------------------------------------

## 14. 分阶段实施

### Phase 1：2--3 周，建立可用地图

目标：先让团队能看懂系统。

范围：

1.  定义 `system-map.json` schema。
2.  选择 1--2 个最重要 Flow。
3.  建立 Flow / Stage / Prompt / Tool / Artifact。
4.  扫描 Prompt。
5.  Graphify 提供 Implementation Graph。
6.  Cytoscape.js 生成静态 HTML。
7.  点击 Stage/Prompt 可以展开详情。
8.  CI 自动重新生成 HTML。

暂不追求完整 Eval 和 AI 问答。

### Phase 2：Runtime Grounding

引入 OpenTelemetry + Langfuse：

``` text
Static Graph
+
Runtime Trace
=
Canonical Execution Graph
```

补充真实 Stage 顺序、Prompt Version、Tool Call、运行频率和 latency。

### Phase 3：Change Intelligence

增加：

-   Prompt Semantic Diff
-   Pipeline Semantic Diff
-   Impact Highlight
-   Dirty-subtree incremental analysis
-   Release comparison
-   PR 自动生成 System Impact Summary

### Phase 4：Ask the System

在图之上增加 Agent：

``` text
“为什么 Research 会多次搜索？”
“哪些 Prompt 影响最终回答？”
“修改 planner 会影响哪些 Flow？”
“这个 Artifact 从哪里产生？”
```

Agent 查询
`system-map.json + code graph + runtime evidence`，而不是直接猜测整个
repo。

------------------------------------------------------------------------

## 15. MVP 成功标准

第一版不需要追求完整知识图谱。

如果团队可以可靠回答下面八个问题，MVP 就已经成功：

1.  这个 Flow 怎么运行？
2.  这个 Stage 是干什么的？
3.  它使用哪些 Prompt？
4.  它输入什么、输出什么？
5.  这个 Prompt 在哪些地方被使用？
6.  这个节点对应什么代码？
7.  修改它可能影响哪些 downstream？
8.  当前版本相比上一版本改变了什么？

------------------------------------------------------------------------

## 16. 最终形态

最终产品可以定义为：

# RepoAtlas

``` text
                     AI System
                        │
               ┌────────┴────────┐
               ↓                 ↓
             Flow              Flow
               │
          ┌────┴────┐
          ↓         ↓
        Stage      Stage
          │
   ┌──────┼──────────┐
   ↓      ↓          ↓
 Prompt  Tool      Artifact
   │                 │
   └────────┬────────┘
            ↓
       Execution Path
            │
            ↓
          Output
            │
       Implementation
            ↓
     Graphify Code Graph
```

每个节点最终应该尽可能回答：

-   What is it?
-   Why does it exist?
-   What goes in?
-   What comes out?
-   Which prompts participate?
-   Which pipeline stages participate?
-   Where is the implementation?
-   What depends on it?
-   When did it change?
-   What may happen if we modify it?

技术组合建议：

``` text
Graphify
+
OpenTelemetry
+
Langfuse
+
Prompt Scanner / Registry
+
自有 system-map.json schema
+
Cytoscape.js
+
Git CI/CD
```

其中最重要的设计决策是：

> **Graphify、Langfuse 等都是数据源；`system-map.json`
> 才是团队长期拥有的系统语义资产。**

这样最终得到的不是一次性架构文档，而是一份能够随着代码、Prompt
和实际运行方式持续演进的 **RepoAtlas**。
