# Codebase System Map

> Turn a code repository into a product-readable system map.

Codebase System Map 接收一个本地代码库，输出一份可以直接分享给产品、运营和新成员的独立 HTML 文档。它关注“产品如何运行”，而不是把目录树或完整调用图原样画出来。

```text
Repository
  → CodeWiki extracts traceable code facts
  → LLM translates implementation into product semantics
  → NetworkX reconstructs module topology
  → Viz.js renders self-contained SVG diagrams
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
- HTML 内嵌 SVG、样式和数据，不依赖 CDN 或本地服务器。
- CodeWiki 分析结果增量缓存，重复生成不必完整重扫。
- 不使用 LiteLLM；只需要 OpenAI-compatible URL、Key 和 Model。

## Requirements

- Python 3.12+
- Node.js 18+
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

也可以在 Windows 开发目录运行：

```powershell
.\scripts\setup.ps1
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
```

旧的 `repo-atlas` 和 `living-map` 命令暂时作为兼容入口保留。

## Output

默认写入 `generated/<repository>/`：

```text
system-map.html   面向人的主要交付物，可作为单文件分享
system-map.md     供工程文档和 Git diff 使用的 Mermaid 版本
system-map.json   供调试、二次渲染和自动化使用的结构化数据
```

产品人员通常只需要 `system-map.html`。Markdown 和 JSON 是工程侧产物，不是阅读 HTML 的依赖。

## Python API

```python
from pathlib import Path
from codebase_map import BuildOptions, build_repository

result = build_repository(
    "/path/to/repository",
    BuildOptions(
        config=Path("/path/to/codebase-map.env"),
        output_directory=Path("/path/to/output"),
        language="zh",
    ),
)

print(result.html)
```

公共边界是：

```text
build_repository(repository, options) -> BuildResult
```

CodeWiki、模型调用、拓扑重建和图形渲染均封装在内部，可以独立替换。

## Architecture

- **Evidence Collector**：从 CodeWiki、架构文档和源码 Prompt 收集带来源的事实。
- **Semantic Synthesizer**：让 LLM 选择运行语义和产品名称，不让模型凭空决定拓扑。
- **Module View Builder**：使用 NetworkX 计算模块接口、内部边、分支和汇合点。
- **Quality Gate**：拒绝孤立节点，检查 canonical edge 是否进入模块视图。
- **Diagram Adapter**：让 Viz.js SVG 和 Mermaid 消费同一份 Module View。
- **Static Exporter**：把图、节点详情和数据内嵌到单个 HTML。

更完整的产品模型见 [codebase_system_map.md](codebase_system_map.md)。开源组件选型与边界记录在 [docs](docs/) 中。

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
scripts/living_map/build.py       构建编排与公共接口实现
scripts/living_map/generator.py   证据、LLM 合成与静态导出
scripts/living_map/topology.py    Module View Builder 与 Quality Gate
scripts/living_map/assets/        随包分发的 Viz.js 渲染适配器
scripts/codebase_map/             新公共 Python 命名空间
```

## Open-source components

Codebase System Map 主要组合以下开源模块：

- [CodeWiki](https://github.com/PorunC/CodeWiki) — 代码结构和关系事实。
- [NetworkX](https://networkx.org/) — 模块拓扑推导。
- [Viz.js](https://viz-js.com/) — Graphviz WebAssembly SVG 渲染。
- [OpenAI Python SDK](https://github.com/openai/openai-python) — OpenAI-compatible API 客户端。

Viz.js 的随包许可证位于 `scripts/living_map/assets/VIZ_JS_LICENSE.txt`。

## License

[MIT](LICENSE)
