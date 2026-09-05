# Codebase System Map

> Turn a code repository into a product-readable system map.

Codebase System Map 接收一个本地代码库，输出一份可以直接分享给产品、运营和新成员的独立 HTML 文档。它关注“产品如何运行”，而不是把目录树或完整调用图原样画出来。

```text
Repository
  → CodeWiki extracts traceable code facts
  → LLM translates implementation into product semantics
  → NetworkX reconstructs module topology
  → standalone HTML renders diagrams locally with bundled Viz.js
  → system-map.html
```

文档按三层组织：

1. 系统总览：主要产品能力及运行主路径。
2. 模块视图：入口、出口、分支、汇合、状态和产物。
3. 节点详情：职责、输入输出、实现位置，以及有源码证据的 Prompt。

生成过程是一次性命令，不启动服务器。完成后可以关闭终端，复制单个 `system-map.html` 给其他人离线阅读。

## Features

- 面向产品语义的系统总览，不输出难以阅读的代码毛线团。
- 每个模块有独立小图，并明确输入、输出和并行分支。
- 普通 Web 应用、后台任务、数据管线和 AI 工作流使用同一入口。
- Prompt 只在代码或文档存在证据时展示，并保留来源路径和行号。
- HTML 内嵌 Viz.js、Graphviz WebAssembly、样式和数据，不依赖 CDN、本地服务器或 Node.js。
- CodeWiki 分析结果增量缓存，重复生成不必完整重扫。
- 不使用 LiteLLM；只需要 OpenAI-compatible URL、Key 和 Model。

## Requirements

- Python 3.12+
- 一个 OpenAI-compatible LLM API

当前版本已在 Windows 完成端到端验证。核心 Python 包和生成的 HTML 不绑定操作系统；macOS/Linux 尚待持续集成验证。

## Quick start

克隆后创建虚拟环境并安装：

```bash
git clone https://github.com/Farmer-Zh/codebase-system-map.git
cd codebase-system-map
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

macOS/Linux：

```bash
source .venv/bin/activate
python -m pip install .
```

## API configuration

在运行目录创建 `.env`：

```dotenv
URL=https://your-provider.example/v1
KEY=your-secret-key
MODEL=your-model-name
```

`.env` 已被 Git 忽略。不要把真实 API Key 提交到仓库。

## Usage

最简命令只有代码库路径：

```bash
codebase-map /path/to/repository
```

Windows 路径示例：

```powershell
codebase-map 'C:\Users\you\Documents\your-project'
```

指定配置、输出位置和语言：

```bash
codebase-map /path/to/repository \
  --config /path/to/codebase-map.env \
  --output /path/to/output \
  --language zh
```

其他选项：

```text
--work-dir PATH     CodeWiki 缓存和 SQLite 数据库目录
--force-analysis    丢弃增量缓存并重新分析
--dry-run           只收集并统计证据，不调用 LLM 或渲染图
--debug-artifacts   额外生成 Markdown 和 JSON 工程产物
```

## Output

默认写入 `generated/<repository>/`：

```text
system-map.html   面向人的主要交付物，可作为单文件分享
```

需要排查生成结果或接入自动化时，使用 `--debug-artifacts` 额外生成
`system-map.md` 和 `system-map.json`。它们不是阅读 HTML 的依赖。

## Architecture

生成流程只有三个内部接口：

~~~text
collect_evidence(...)     -> EvidenceBundle
compile_system_map(...)   -> SystemMap
export_system_map(...)    -> ArtifactSet
~~~

- **Evidence Collector**：隐藏 CodeWiki 数据库、架构文档和源码 Prompt 的扫描细节。
- **System Map Compiler**：让 LLM 选择运行语义和产品名称，再使用 NetworkX 构造模块接口、分支和汇合点，并执行结构质量检查。
- **Document Exporter**：把 Viz.js 和 Graphviz WebAssembly 内嵌到 HTML，让浏览器离线生成 SVG；调试模式下再导出 Mermaid 和 JSON。

build_repository(...) 只负责编排这三个阶段；数据通过 EvidenceBundle、SystemMap 和 ArtifactSet 显式传递。

开源组件选型与早期设计研究记录在 [docs](docs/) 中。

## Development

运行测试：

```bash
python -m unittest discover -s tests -v
```

构建 wheel：

```bash
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
```

主要实现位于：

```text
src/codebase_map/                 唯一的应用包
  build.py                        CodeWiki 调用与完整构建流程
  evidence.py                     代码库与 CodeWiki 证据收集
  compiler.py                     LLM 合成、规范化与结构验证
  document.py                     standalone HTML 与调试产物
  topology.py                     Module View Builder 与 Quality Gate
  assets/                         内嵌到 HTML 的 Viz.js
```

## Open-source components

Codebase System Map 主要组合以下开源模块：

- [CodeWiki](https://github.com/PorunC/CodeWiki) — 代码结构和关系事实。
- [NetworkX](https://networkx.org/) — 模块拓扑推导。
- [Viz.js](https://viz-js.com/) — Graphviz WebAssembly SVG 渲染。
- [OpenAI Python SDK](https://github.com/openai/openai-python) — OpenAI-compatible API 客户端。

Viz.js 的随包许可证位于 `src/codebase_map/assets/VIZ_JS_LICENSE.txt`。

## License

[MIT](LICENSE)
