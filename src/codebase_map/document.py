"""Render and write every shareable representation of a system map."""

from __future__ import annotations

import base64
import html
import json
import re
from pathlib import Path
from typing import Any

from .models import ArtifactSet, SystemMap
from .topology import module_edge_details, module_view_for


def dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def system_dot(system_map: dict[str, Any]) -> str:
    lines = [
        "digraph G {",
        'graph [rankdir=LR, bgcolor="transparent", pad="0.3", nodesep="0.5", ranksep="0.75", splines=ortho];',
        'node [shape=box, style="rounded,filled", fontname="Arial", fontsize=16, color="#7c93c3", fillcolor="#eef3ff", fontcolor="#172033", penwidth=1.4, margin="0.22,0.16"];',
        'edge [color="#4f6b9a", penwidth=1.7, arrowsize=0.8];',
    ]
    for module in system_map["modules"]:
        label = module["name"]
        lines.append(
            f'"{dot_escape(module["id"])}" [label="{dot_escape(label)}", URL="#module-{dot_escape(module["id"])}", target="_top"];'
        )
    edges = module_edge_details(system_map)
    if not edges:
        ids = [module["id"] for module in system_map["modules"]]
        edges = [{"from": source, "to": target, "primary": True} for source, target in zip(ids, ids[1:])]
    for edge in edges:
        if edge["primary"]:
            attributes = ' [weight=8]'
        else:
            attributes = ' [style="dashed", color="#a8b2c3", constraint=false, arrowsize=0.65]'
        lines.append(
            f'"{dot_escape(edge["from"])}" -> "{dot_escape(edge["to"])}"{attributes};'
        )
    lines.append("}")
    return "\n".join(lines)


def module_dot(system_map: dict[str, Any], module_id: str) -> str:
    nodes = [node for node in system_map["nodes"] if node["module_id"] == module_id]
    ids = {node["id"] for node in nodes}
    all_nodes = {node["id"]: node for node in system_map["nodes"]}
    view = module_view_for(system_map, module_id)
    internal = list(view["internal_edges"])
    incoming_groups = list(view["interfaces"]["inputs"])
    outgoing_groups = list(view["interfaces"]["outputs"])
    incoming = [edge for group in incoming_groups for edge in group["connections"]]
    outgoing = [edge for group in outgoing_groups for edge in group["connections"]]
    incoming_sources = [group["external_node_id"] for group in incoming_groups]
    outgoing_targets = [group["external_node_id"] for group in outgoing_groups]
    colors = {
        "entry": "#dbeafe",
        "stage": "#f8fafc",
        "llm": "#ede9fe",
        "tool": "#dcfce7",
        "store": "#fef3c7",
        "output": "#ffe4e6",
    }
    lines = [
        "digraph G {",
        f'graph [rankdir={"TB" if view["topology"] in {"parallel", "branched", "network"} else "LR"}, bgcolor="transparent", pad="0.25", nodesep="0.45", ranksep="0.72", splines=polyline, pack=true, packmode="array_u2"];',
        'node [shape=box, style="rounded,filled", fontname="Arial", fontsize=13, color="#94a3b8", fontcolor="#172033", penwidth=1.2, margin="0.18,0.12"];',
        'edge [color="#64748b", fontname="Arial", fontsize=10, arrowsize=0.75];',
    ]
    for node_id in incoming_sources:
        external = all_nodes.get(node_id, {"name": node_id})
        label = f'来自 {external["name"]}\n任务 / 数据输入'
        lines.append(
            f'"ext-in-{dot_escape(node_id)}" [label="{dot_escape(label)}", shape=box, style="rounded,dashed,filled", fillcolor="#eef2f6", color="#98a2b3", URL="#node-{dot_escape(node_id)}", target="_top"];'
        )
    for node_id in outgoing_targets:
        external = all_nodes.get(node_id, {"name": node_id})
        label = f'送往 {external["name"]}\n结果 / 状态回写'
        lines.append(
            f'"ext-out-{dot_escape(node_id)}" [label="{dot_escape(label)}", shape=box, style="rounded,dashed,filled", fillcolor="#eef2f6", color="#98a2b3", URL="#node-{dot_escape(node_id)}", target="_top"];'
        )
    for node in nodes:
        prompt_mark = "  · Prompt" if node["prompts"] else ""
        label = f'{node["name"]}\n{node["kind"]}{prompt_mark}'
        lines.append(
            f'"{dot_escape(node["id"])}" [label="{dot_escape(label)}", fillcolor="{colors[node["kind"]]}", URL="#node-{dot_escape(node["id"])}", target="_top"];'
        )
    for edge in internal:
        label = f' [label="{dot_escape(edge["label"])}"]' if edge["label"] else ""
        lines.append(f'"{dot_escape(edge["from"])}" -> "{dot_escape(edge["to"])}"{label};')
    for edge in incoming:
        label = f' [label="{dot_escape(edge["label"])}"]' if edge["label"] else ""
        lines.append(
            f'"ext-in-{dot_escape(edge["from"])}" -> "{dot_escape(edge["to"])}"{label};'
        )
    for edge in outgoing:
        label = f' [label="{dot_escape(edge["label"])}"]' if edge["label"] else ""
        lines.append(
            f'"{dot_escape(edge["from"])}" -> "ext-out-{dot_escape(edge["to"])}"{label};'
        )
    lines.append("}")
    return "\n".join(lines)


def diagram_sources(system_map: dict[str, Any]) -> dict[str, str]:
    """Return Graphviz sources for browser-side offline rendering."""
    diagrams = {"system": system_dot(system_map)}
    for module in system_map["modules"]:
        diagrams[f'module:{module["id"]}'] = module_dot(system_map, module["id"])
    return diagrams


def mermaid_id(value: str) -> str:
    return "n_" + re.sub(r"[^a-zA-Z0-9_]", "_", value)


def mermaid_label(value: str) -> str:
    return value.replace('"', "'").replace("\n", " ")


def markdown_output(system_map: dict[str, Any]) -> str:
    lines = [
        f'# {system_map["system"]["name"]}',
        "",
        system_map["system"]["summary"],
        "",
        "## 系统总览",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    for module in system_map["modules"]:
        lines.append(f'  {mermaid_id(module["id"])}["{mermaid_label(module["name"])}"]')
    for edge in module_edge_details(system_map):
        connector = "-->" if edge["primary"] else "-.->"
        lines.append(f'  {mermaid_id(edge["from"])} {connector} {mermaid_id(edge["to"])}')
    lines.extend(["```", ""])
    for module in system_map["modules"]:
        nodes = [node for node in system_map["nodes"] if node["module_id"] == module["id"]]
        node_ids = {node["id"] for node in nodes}
        all_nodes = {node["id"]: node for node in system_map["nodes"]}
        view = module_view_for(system_map, module["id"])
        incoming_groups = list(view["interfaces"]["inputs"])
        outgoing_groups = list(view["interfaces"]["outputs"])
        incoming = [edge for group in incoming_groups for edge in group["connections"]]
        outgoing = [edge for group in outgoing_groups for edge in group["connections"]]
        direction = "TB" if view["topology"] in {"parallel", "branched", "network"} else "LR"
        lines.extend([f'## {module["name"]}', "", module["responsibility"], "", "```mermaid", f"flowchart {direction}"])
        for node_id in (group["external_node_id"] for group in incoming_groups):
            name = all_nodes.get(node_id, {"name": node_id})["name"]
            lines.append(f'  ext_in_{mermaid_id(node_id)}[["来自 {mermaid_label(name)} · 输入"]]')
        for node in nodes:
            lines.append(f'  {mermaid_id(node["id"])}["{mermaid_label(node["name"])}"]')
        for node_id in (group["external_node_id"] for group in outgoing_groups):
            name = all_nodes.get(node_id, {"name": node_id})["name"]
            lines.append(f'  ext_out_{mermaid_id(node_id)}[["送往 {mermaid_label(name)} · 回写"]]')
        for edge in view["internal_edges"]:
            label = mermaid_label(edge["label"] or edge["type"]).replace("|", "/")
            lines.append(f'  {mermaid_id(edge["from"])} -->|"{label}"| {mermaid_id(edge["to"])}')
        for edge in incoming:
            label = mermaid_label(edge["label"] or edge["type"]).replace("|", "/")
            lines.append(f'  ext_in_{mermaid_id(edge["from"])} -->|"{label}"| {mermaid_id(edge["to"])}')
        for edge in outgoing:
            label = mermaid_label(edge["label"] or edge["type"]).replace("|", "/")
            lines.append(f'  {mermaid_id(edge["from"])} -->|"{label}"| ext_out_{mermaid_id(edge["to"])}')
        lines.extend(["```", ""])
        for node in nodes:
            lines.extend(
                [
                    f'### {node["name"]}',
                    "",
                    node["purpose"],
                    "",
                    f'- 输入：{", ".join(node["inputs"]) or "—"}',
                    f'- 输出：{", ".join(node["outputs"]) or "—"}',
                    f'- 实现：{", ".join(f"`{path}`" for path in node["implementation"]) or "—"}',
                    "",
                ]
            )
            if not node["prompts"]:
                lines.extend(["Prompt：此节点不直接调用 LLM，或未发现 Prompt 证据。", ""])
            for prompt in node["prompts"]:
                prompt_label = "源码 Prompt" if prompt["evidence_kind"] == "source_prompt" else "文档 Prompt"
                if prompt.get("truncated"):
                    prompt_label += "（节选）"
                lines.extend(
                    [
                        f'{prompt_label}：`{prompt["source_path"]}:{prompt["start_line"]}`',
                        "",
                        "```text",
                        prompt["content"],
                        "```",
                        "",
                    ]
                )
    return "\n".join(lines).strip() + "\n"


def chips(values: list[str]) -> str:
    if not values:
        return '<span class="empty">—</span>'
    return "".join(f'<span class="chip">{html.escape(value)}</span>' for value in values)


def html_output(
    system_map: dict[str, Any],
    diagrams: dict[str, str],
    viz_module_base64: str,
) -> str:
    modules_html: list[str] = []
    topology_names = {
        "single": "单节点",
        "pipeline": "流水线",
        "parallel": "并行分支",
        "branched": "分支流程",
        "network": "循环网络",
    }
    for module in system_map["modules"]:
        nodes = [node for node in system_map["nodes"] if node["module_id"] == module["id"]]
        view = module_view_for(system_map, module["id"])
        metrics = view["metrics"]
        topology_text = topology_names.get(view["topology"], view["topology"])
        if metrics["branch_count"] > 1:
            topology_text += f' · {metrics["branch_count"]} 个分支'
        node_cards: list[str] = []
        for node in nodes:
            prompt_html = ""
            if node["prompts"]:
                prompt_blocks = []
                for prompt in node["prompts"]:
                    prompt_title = "源码 Prompt" if prompt["evidence_kind"] == "source_prompt" else "文档 Prompt"
                    if prompt.get("truncated"):
                        prompt_title += "（节选）"
                    prompt_blocks.append(
                        f'<h6>{prompt_title}</h6>'
                        f'<div class="prompt-source">{html.escape(prompt["source_path"])}:{prompt["start_line"]}-{prompt["end_line"]}</div>'
                        f'<pre>{html.escape(prompt["content"])}</pre>'
                    )
                prompt_html = '<div class="prompt"><h5>实际 Prompt</h5>' + "".join(prompt_blocks) + "</div>"
            else:
                prompt_html = '<div class="no-prompt">不直接调用 LLM，或未发现 Prompt 证据</div>'
            node_cards.append(
                f'''<details class="node-card" id="node-{html.escape(node["id"])}" data-search="{html.escape((node["name"] + ' ' + node["purpose"] + ' ' + ' '.join(node["implementation"])).lower())}">
<summary><span class="kind {html.escape(node["kind"])}">{html.escape(node["kind"])}</span><strong>{html.escape(node["name"])}</strong><span class="summary-purpose">{html.escape(node["purpose"])}</span></summary>
<div class="node-body"><div class="io"><div><h5>输入</h5>{chips(node["inputs"])}</div><div><h5>输出</h5>{chips(node["outputs"])}</div></div>
<div class="implementation"><h5>实现位置</h5>{chips(node["implementation"])}</div>{prompt_html}</div>
</details>'''
            )
        modules_html.append(
            f'''<section class="module" id="module-{html.escape(module["id"])}">
<div class="module-heading"><div><span class="eyebrow">MODULE</span><span class="topology">{html.escape(topology_text)}</span><h2>{html.escape(module["name"])}</h2><p>{html.escape(module["responsibility"])}</p></div><div class="module-paths">{chips(module["source_paths"])}</div></div>
<div class="diagram-key"><span></span>虚线节点表示该模块的外部接口</div>
<div class="diagram module-diagram" data-diagram="module:{html.escape(module['id'])}"><span class="empty">正在绘制...</span></div>
<div class="nodes">{''.join(node_cards)}</div>
</section>'''
        )
    navigation = "".join(
        f'<a href="#module-{html.escape(module["id"])}">{html.escape(module["name"])}</a>'
        for module in system_map["modules"]
    )
    overview_legend = "".join(
        f'<a class="overview-module" href="#module-{html.escape(module["id"])}"><strong>{html.escape(module["name"])}</strong><span>{html.escape(module["responsibility"])}</span></a>'
        for module in system_map["modules"]
    )
    map_json = json.dumps(system_map, ensure_ascii=False).replace("</", "<\\/")
    diagram_json = json.dumps(diagrams, ensure_ascii=False).replace("</", "<\\/")
    viz_json = json.dumps(viz_module_base64)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(system_map["system"]["name"])} · System Map</title>
<style>
:root{{--ink:#172033;--muted:#667085;--line:#d8dee9;--paper:#f4f7fb;--card:#fff;--blue:#2457d6;--blue-soft:#eaf0ff;--violet:#6d3fc0;--green:#13795b;--amber:#9a6700}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.65 Inter,"Segoe UI","Microsoft YaHei",sans-serif}}
.top{{background:#101828;color:white;padding:52px max(24px,calc((100vw - 1180px)/2));border-bottom:5px solid #4f7cff}}.eyebrow{{font-size:11px;font-weight:800;letter-spacing:.14em;color:#7aa2ff}}h1{{font-size:38px;line-height:1.15;margin:8px 0 14px}}.top p{{max-width:780px;color:#d0d5dd;font-size:17px;margin:0}}
.sticky{{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}}.nav{{max-width:1180px;margin:auto;padding:10px 20px;display:flex;gap:8px;overflow:auto}}.nav a{{white-space:nowrap;text-decoration:none;color:#344054;padding:7px 11px;border-radius:8px}}.nav a:hover{{background:var(--blue-soft);color:var(--blue)}}
main{{max-width:1180px;margin:auto;padding:28px 20px 80px}}.overview,.module{{background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 8px 30px rgba(16,24,40,.05)}}.overview{{padding:28px;margin-bottom:28px}}h2{{font-size:26px;margin:4px 0 8px}}p{{color:var(--muted)}}
.diagram{{overflow:auto;background:#fbfcfe;border:1px solid #e6eaf0;border-radius:12px;padding:22px}}.diagram svg{{display:block;max-width:none;height:auto;margin:auto}}.overview-modules{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;margin-top:14px}}.overview-module{{display:flex;flex-direction:column;gap:3px;padding:12px 14px;border:1px solid var(--line);border-radius:10px;text-decoration:none;color:var(--ink);background:#fff}}.overview-module:hover{{border-color:#8da7e8;background:#f7f9ff}}.overview-module span{{font-size:13px;line-height:1.45;color:var(--muted)}}.module{{padding:28px;margin:24px 0;scroll-margin-top:70px}}.module-heading{{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:18px}}.module-heading p{{max-width:720px;margin:0}}.module-paths{{max-width:380px;text-align:right}}
.diagram-key{{display:flex;align-items:center;gap:7px;margin:0 0 8px;color:#7b8494;font-size:12px}}.diagram-key span{{width:22px;height:12px;border:1.5px dashed #98a2b3;border-radius:4px;background:#eef2f6}}
.topology{{display:inline-block;margin-left:8px;padding:2px 7px;border-radius:999px;background:#eef2f6;color:#596273;font-size:11px;font-weight:700}}
.nodes{{display:grid;gap:10px;margin-top:18px}}.node-card{{border:1px solid var(--line);border-radius:11px;background:#fff;scroll-margin-top:76px}}.node-card[open]{{border-color:#9bb2ef;box-shadow:0 4px 16px rgba(36,87,214,.08)}}summary{{cursor:pointer;list-style:none;display:grid;grid-template-columns:auto minmax(140px,240px) 1fr;align-items:center;gap:12px;padding:14px 16px}}summary::-webkit-details-marker{{display:none}}.summary-purpose{{color:var(--muted)}}
.kind{{font-size:10px;text-transform:uppercase;font-weight:800;padding:3px 7px;border-radius:999px;background:#eef2f6}}.kind.llm{{color:var(--violet);background:#f1eafe}}.kind.store{{color:var(--amber);background:#fff4ce}}.kind.tool{{color:var(--green);background:#dcfae6}}.kind.entry,.kind.output{{color:var(--blue);background:var(--blue-soft)}}
.node-body{{border-top:1px solid var(--line);padding:18px}}.io{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}h5{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#667085;margin:0 0 8px}}.chip{{display:inline-block;padding:4px 8px;margin:2px 4px 2px 0;background:#f2f4f7;border-radius:7px;color:#344054;font-size:13px}}.implementation,.prompt,.no-prompt{{margin-top:16px}}.prompt{{border-top:1px solid var(--line);padding-top:16px}}.prompt-source{{font:12px/1.5 Consolas,monospace;color:var(--blue);margin-bottom:6px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;background:#101828;color:#e4e7ec;border-radius:9px;padding:16px;font:12px/1.6 Consolas,monospace}}.no-prompt,.empty{{color:#98a2b3;font-size:13px}}
h6{{font-size:13px;margin:12px 0 3px}}
@media(max-width:760px){{h1{{font-size:30px}}.module-heading{{display:block}}.module-paths{{text-align:left;max-width:none;margin-top:12px}}summary{{grid-template-columns:auto 1fr}}.summary-purpose{{grid-column:1/-1}}.io{{grid-template-columns:1fr}}}}
</style></head><body>
<header class="top"><span class="eyebrow">CODEBASE SYSTEM MAP</span><h1>{html.escape(system_map["system"]["name"])}</h1><p>{html.escape(system_map["system"]["summary"])}</p></header>
<div class="sticky"><nav class="nav"><a href="#overview">系统总览</a>{navigation}</nav></div>
<main><section class="overview" id="overview"><span class="eyebrow">SYSTEM FLOW</span><h2>整体架构</h2><p>实线表示主调用路径；虚线表示读取、写入、返回或慢任务关系。点击模块可下钻。</p><div class="diagram" data-diagram="system"><span class="empty">正在绘制...</span></div><div class="overview-modules">{overview_legend}</div></section>{''.join(modules_html)}</main>
<script type="application/json" id="system-map-data">{map_json}</script>
<script type="application/json" id="diagram-data">{diagram_json}</script>
<script type="module">
try {{
  const encoded = {viz_json};
  const vizModule = await import("data:text/javascript;base64," + encoded);
  const viz = await vizModule.instance();
  const sources = JSON.parse(document.getElementById("diagram-data").textContent);
  for (const target of document.querySelectorAll("[data-diagram]")) {{
    const dot = sources[target.dataset.diagram];
    if (dot) target.innerHTML = viz.renderString(dot, {{format: "svg", engine: "dot"}});
  }}
}} catch (error) {{
  for (const target of document.querySelectorAll("[data-diagram]")) {{
    target.innerHTML = '<span class="empty">图形渲染失败：' + String(error) + '</span>';
  }}
}}
</script>
</body></html>'''


def export_system_map(
    system_map: SystemMap,
    output_directory: Path,
    *,
    debug_artifacts: bool = False,
) -> ArtifactSet:
    """Write the standalone HTML and optional engineering artifacts."""
    output = output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    diagrams = diagram_sources(system_map)
    viz_module_base64 = base64.b64encode(
        (Path(__file__).parent / "assets" / "viz.js").read_bytes()
    ).decode("ascii")
    artifacts = ArtifactSet(
        html=output / "system-map.html",
        markdown=(output / "system-map.md") if debug_artifacts else None,
        data=(output / "system-map.json") if debug_artifacts else None,
    )
    artifacts.html.write_text(
        html_output(system_map, diagrams, viz_module_base64),
        encoding="utf-8",
    )
    if artifacts.data and artifacts.markdown:
        artifacts.data.write_text(
            json.dumps(system_map, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        artifacts.markdown.write_text(markdown_output(system_map), encoding="utf-8")
    return artifacts


__all__ = ["export_system_map"]
