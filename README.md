# Codebase System Map

> Give it a repository. Get one product-readable system map.

[中文](#中文) · [English](#english)

Codebase System Map analyzes a local code repository and generates one standalone
`system-map.html`. The document explains the product's runtime architecture at
three levels: the whole system, each module, and each important node.

It runs as a one-time command. It does not start a server, and the generated HTML
can be opened or shared after the terminal is closed.

~~~text
Repository
  → CodeWiki extracts traceable code facts
  → LLM translates implementation into product concepts
  → NetworkX reconstructs module topology
  → bundled Viz.js renders diagrams in the browser
  → standalone system-map.html
~~~

## 中文

### 它生成什么

输入一个本地代码库，输出一份面向产品经理、运营人员和新成员的系统说明：

1. **系统总览**：主要产品能力及核心运行路径。
2. **模块视图**：每个模块的入口、出口、分支、汇合、状态和产物。
3. **节点详情**：职责、输入、输出、实现位置，以及有源码证据的 Prompt。

主要交付物只有一个文件：

~~~text
generated/<仓库名>/system-map.html
~~~

HTML 已内嵌样式、数据、Viz.js 和 Graphviz WebAssembly，不依赖 CDN、Node.js
或本地服务器。生成完成后可以关闭 PowerShell，直接双击打开，或者把这一个
HTML 文件发给其他人离线阅读。

### 环境要求

- Python 3.12 或更高版本
- Git
- 一个兼容 OpenAI 接口的 LLM API
- Windows PowerShell、macOS 或 Linux

项目已在 Windows 上完成端到端验证。Python 包和生成的 HTML 均不绑定操作系统。

### 安装

克隆项目：

~~~powershell
git clone https://github.com/Farmer-Zh/codebase-system-map.git
cd codebase-system-map
~~~

#### Windows PowerShell

创建虚拟环境并安装：

~~~powershell
py -3.12 -m venv .venv
..venvScriptspython.exe -m pip install .
~~~

无需激活虚拟环境，直接运行：

~~~powershell
..venvScriptscodebase-map.exe 'C:path	oyour-repository'
~~~

也可以先激活，再使用短命令：

~~~powershell
..venvScriptsActivate.ps1
codebase-map 'C:path	oyour-repository'
~~~

如果 PowerShell 禁止运行 `Activate.ps1`，不必修改执行策略；使用上面的
`..venvScriptscodebase-map.exe` 即可。

#### macOS / Linux

~~~bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install .
codebase-map /path/to/your-repository
~~~

### 配置 LLM

在运行命令的目录创建 `.env`：

~~~dotenv
URL=https://your-provider.example/v1
KEY=your-secret-key
MODEL=your-model-name
~~~

只需要这三个字段。`.env` 已被 Git 忽略，请勿提交真实 API Key。

也可以把配置文件放在其他位置：

~~~powershell
..venvScriptscodebase-map.exe 'C:path	oepo' --config 'C:path	oapi.env'
~~~

### 生成系统图

Windows：

~~~powershell
..venvScriptscodebase-map.exe 'C:UsersyouDocumentsyour-project'
~~~

macOS / Linux：

~~~bash
codebase-map /path/to/your-project
~~~

默认输出到当前目录的 `generated/<仓库名>/system-map.html`。指定输出位置：

~~~powershell
..venvScriptscodebase-map.exe 'C:path	oepo' --output 'D:mapsmy-project'
~~~

### 输出语言

默认参数是 `--language auto`。程序读取项目根目录的 README、CONTEXT 和架构
文档，判断项目说明文字主要使用中文还是英文，然后让以下内容保持同一种语言：

- LLM 生成的系统名称、模块名称和产品说明
- HTML 的导航、标题、图例和状态文字
- 调试模式生成的 Markdown

自动模式当前识别中文和英文。没有可用文档时默认使用英文。可以显式覆盖：

~~~powershell
# 强制中文
..venvScriptscodebase-map.exe 'C:path	oepo' --language zh

# 强制英文
..venvScriptscodebase-map.exe 'C:path	oepo' --language en
~~~

这里判断的是项目文档的自然语言，不是 Python、Go 或 TypeScript 等编程语言。

### 常用参数

| 参数 | 作用 |
| --- | --- |
| `-o, --output PATH` | 指定输出目录 |
| `--config PATH` | 指定包含 URL、KEY、MODEL 的配置文件 |
| `--language auto\|zh\|en` | 自动判断或强制输出语言 |
| `--work-dir PATH` | 指定 CodeWiki 缓存和 SQLite 数据库目录 |
| `--force-analysis` | 丢弃增量缓存并重新分析 |
| `--dry-run` | 只收集和统计证据，不调用 LLM、不生成文件 |
| `--debug-artifacts` | 额外生成 Markdown 和 JSON |
| `--version` | 显示版本 |

完整帮助：

~~~powershell
..venvScriptscodebase-map.exe --help
~~~

### 输出文件

默认只生成：

~~~text
system-map.html   面向人阅读和分享的独立文档
~~~

需要排查生成内容或接入自动化时：

~~~powershell
..venvScriptscodebase-map.exe 'C:path	oepo' --debug-artifacts
~~~

此时额外生成：

~~~text
system-map.md     Mermaid 版工程文档
system-map.json   结构化系统图数据
~~~

这两个调试文件不是打开或分享 HTML 的必要条件。

### 重复运行与更新

CodeWiki 的分析结果保存在 `.codebase-map/`，再次生成时会增量分析。只有需要
完全重扫代码库时才使用 `--force-analysis`。

拉取本项目的新版本后，重新安装包：

~~~powershell
git pull
..venvScriptspython.exe -m pip install . --no-deps --force-reinstall
~~~

### 工作原理

项目只有三个主要内部接口：

~~~text
collect_evidence(...)     → EvidenceBundle
compile_system_map(...)   → SystemMap
export_system_map(...)    → ArtifactSet
~~~

- **Evidence Collector** 隐藏 CodeWiki 数据库、架构文档和源码 Prompt 的扫描细节。
- **System Map Compiler** 使用 LLM 将代码事实转成产品语义，再由 NetworkX 构造
  模块接口、分支和汇合点并检查结构质量。
- **Document Exporter** 把 Viz.js 和 Graphviz WebAssembly 内嵌到 HTML；调试
  模式下再导出 Mermaid 和 JSON。

## English

### What it produces

Pass a local repository to the command. It produces a system map for product
managers, operators, and engineers who are new to the codebase:

1. **System overview** — the main product capabilities and primary runtime path.
2. **Module views** — inputs, outputs, branches, joins, state, and artifacts.
3. **Node details** — purpose, inputs, outputs, implementation paths, and
   evidence-backed prompts.

The primary deliverable is one file:

~~~text
generated/<repository>/system-map.html
~~~

The HTML contains its styles, data, Viz.js, and Graphviz WebAssembly. It needs no
CDN, Node.js runtime, or local server. Once generation finishes, close the terminal
and open or share the HTML file directly.

### Requirements

- Python 3.12 or newer
- Git
- An OpenAI-compatible LLM API
- Windows PowerShell, macOS, or Linux

The complete workflow is verified on Windows. The Python package and generated
HTML are platform-independent.

### Install

Clone the repository:

~~~bash
git clone https://github.com/Farmer-Zh/codebase-system-map.git
cd codebase-system-map
~~~

#### Windows PowerShell

Create a virtual environment and install the package:

~~~powershell
py -3.12 -m venv .venv
..venvScriptspython.exe -m pip install .
~~~

Run it directly without activating the environment:

~~~powershell
..venvScriptscodebase-map.exe 'C:path	oyour-repository'
~~~

Or activate the environment and use the short command:

~~~powershell
..venvScriptsActivate.ps1
codebase-map 'C:path	oyour-repository'
~~~

If PowerShell blocks `Activate.ps1`, you do not need to change the execution
policy. Use `..venvScriptscodebase-map.exe` directly.

#### macOS / Linux

~~~bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install .
codebase-map /path/to/your-repository
~~~

### Configure the LLM

Create `.env` in the directory where you run the command:

~~~dotenv
URL=https://your-provider.example/v1
KEY=your-secret-key
MODEL=your-model-name
~~~

These are the only required settings. The repository ignores `.env`; never
commit a real API key.

To use a config file elsewhere:

~~~powershell
..venvScriptscodebase-map.exe 'C:path	oepo' --config 'C:path	oapi.env'
~~~

### Generate a map

Windows:

~~~powershell
..venvScriptscodebase-map.exe 'C:UsersyouDocumentsyour-project'
~~~

macOS / Linux:

~~~bash
codebase-map /path/to/your-project
~~~

By default, the result is written to
`generated/<repository>/system-map.html` under the current directory. To select
another destination:

~~~powershell
..venvScriptscodebase-map.exe 'C:path	oepo' --output 'D:mapsmy-project'
~~~

### Output language

The default is `--language auto`. The program reads the root README, CONTEXT,
and architecture documents, determines whether the project's prose is primarily
Chinese or English, and uses that language consistently for:

- LLM-generated system names, module names, and product explanations
- HTML navigation, headings, legends, and status text
- Markdown produced in debug mode

Automatic mode currently detects Chinese and English. It defaults to English when
no suitable documents are available. Override it when needed:

~~~powershell
# Force Chinese
..venvScriptscodebase-map.exe 'C:path	oepo' --language zh

# Force English
..venvScriptscodebase-map.exe 'C:path	oepo' --language en
~~~

This detects the natural language of project documentation, not a programming
language such as Python, Go, or TypeScript.

### Options

| Option | Purpose |
| --- | --- |
| `-o, --output PATH` | Select the output directory |
| `--config PATH` | Select the file containing URL, KEY, and MODEL |
| `--language auto\|zh\|en` | Detect or override the output language |
| `--work-dir PATH` | Select the CodeWiki cache and SQLite directory |
| `--force-analysis` | Discard the incremental cache and analyze again |
| `--dry-run` | Collect and size evidence without calling the LLM or writing output |
| `--debug-artifacts` | Also write Markdown and JSON |
| `--version` | Show the installed version |

Show the complete command help:

~~~powershell
..venvScriptscodebase-map.exe --help
~~~

### Output files

The default build writes only:

~~~text
system-map.html   Standalone document for reading and sharing
~~~

For diagnostics or automation:

~~~powershell
..venvScriptscodebase-map.exe 'C:path	oepo' --debug-artifacts
~~~

This also writes:

~~~text
system-map.md     Engineering-oriented Mermaid document
system-map.json   Structured system-map data
~~~

Neither debug file is required to open or share the HTML.

### Repeated runs and updates

CodeWiki keeps its analysis in `.codebase-map/`. Later runs analyze changes
incrementally. Use `--force-analysis` only when you need a complete rescan.

After pulling a new version of this project, reinstall the package:

~~~powershell
git pull
..venvScriptspython.exe -m pip install . --no-deps --force-reinstall
~~~

### Architecture

The package exposes three main internal seams:

~~~text
collect_evidence(...)     → EvidenceBundle
compile_system_map(...)   → SystemMap
export_system_map(...)    → ArtifactSet
~~~

- **Evidence Collector** hides CodeWiki database access and scanning for
  architecture documents and source prompts.
- **System Map Compiler** uses an LLM to translate code facts into product
  semantics, then uses NetworkX to reconstruct interfaces, branches, and joins
  and to run structural quality checks.
- **Document Exporter** embeds Viz.js and Graphviz WebAssembly in the HTML and
  optionally exports Mermaid and JSON in debug mode.

## Development

Run tests:

~~~bash
python -m unittest discover -s tests -v
~~~

Build a wheel:

~~~bash
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
~~~

Main source layout:

~~~text
src/codebase_map/
  build.py          CodeWiki invocation and build orchestration
  evidence.py       Repository and CodeWiki evidence collection
  compiler.py       Language selection, LLM synthesis, and normalization
  topology.py       Module views and structural quality checks
  document.py       Standalone HTML and debug exports
  assets/           Viz.js embedded in generated HTML
~~~

## Open-source components

- [CodeWiki](https://github.com/PorunC/CodeWiki) — traceable code structure and relationships
- [NetworkX](https://networkx.org/) — topology reconstruction
- [Viz.js](https://viz-js.com/) — Graphviz WebAssembly SVG rendering
- [OpenAI Python SDK](https://github.com/openai/openai-python) — OpenAI-compatible API client

The bundled Viz.js license is stored at
`src/codebase_map/assets/VIZ_JS_LICENSE.txt`.

## License

[MIT](LICENSE)
