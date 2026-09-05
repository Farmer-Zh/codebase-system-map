"""Build a diagram-first system map from code and repository evidence."""

from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from living_map.topology import enrich_system_map, module_edge_details, module_view_for


TEXT_SUFFIXES = {".md", ".txt", ".go", ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs"}
IGNORED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "vendor",
    "generated",
    "dist",
    "build",
    "analysis",
    "artifacts",
    ".tmp",
    "references",
    "eveexample",
    "prototypes",
    "development-plans",
}
NON_RUNTIME_TOP_LEVEL = {
    ".github",
    ".codex",
    "docs",
    "development-plans",
    "prototypes",
    "references",
    "eveexample",
    "tmp",
}
PROMPT_CONTEXT_TERMS = (
    "prompt",
    "system message",
    "system_message",
    "system prompt",
    "提示词",
    "提示",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_id")
    parser.add_argument("repository")
    parser.add_argument("output_directory")
    parser.add_argument("--database", default="data/codewiki.sqlite3")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--config", default=".env")
    parser.add_argument("--node", default="node")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def read_api_config(path: Path) -> tuple[str, str, str]:
    from dotenv import dotenv_values

    values = dotenv_values(path)
    url = str(values.get("URL") or "").strip()
    key = str(values.get("KEY") or "").strip()
    model = str(values.get("MODEL") or "").strip()
    if not all((url, key, model)):
        raise ValueError(f"Set URL, KEY and MODEL in {path}")
    return url, key, model


def repository_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if any(part.lower() in IGNORED_PARTS for part in relative.parts):
            continue
        try:
            if path.stat().st_size > 500_000:
                continue
        except OSError:
            continue
        files.append(path)
    return files


def document_rank(relative: str) -> tuple[int, int, str]:
    lower = relative.lower()
    name = PurePosixPath(relative).name.lower()
    if name == "context.md":
        rank = 0
    elif name == "readme.md" and "/" not in relative:
        rank = 1
    elif "runtime-architecture" in lower or "current-runtime-flow" in lower:
        rank = 2
    elif "prompt-architecture" in lower:
        rank = 3
    elif "architecture" in lower:
        rank = 4
    elif "prompt" in lower:
        rank = 5
    elif name in {"agents.md", "documentation_index.md", "project_state.md"}:
        rank = 6
    else:
        rank = 20
    return rank, relative.count("/"), relative


def load_evidence_documents(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    candidates: list[tuple[tuple[int, int, str], Path]] = []
    for path in files:
        if path.suffix.lower() != ".md":
            continue
        relative = path.relative_to(root).as_posix()
        rank = document_rank(relative)
        if rank[0] < 20:
            candidates.append((rank, path))
    candidates.sort(key=lambda item: item[0])

    documents: list[dict[str, Any]] = []
    total_chars = 0
    for _, path in candidates:
        if len(documents) >= 8 or total_chars >= 50_000:
            break
        full_content = path.read_text(encoding="utf-8", errors="replace")
        remaining = 50_000 - total_chars
        content = full_content[: min(10_000, remaining)]
        if not content.strip():
            continue
        relative = path.relative_to(root).as_posix()
        numbered = "\n".join(
            f"{index}: {line}" for index, line in enumerate(content.splitlines(), start=1)
        )
        documents.append(
            {
                "path": relative,
                "content": numbered,
                "truncated": len(content) < len(full_content),
                "original_chars": len(full_content),
                "included_chars": len(content),
            }
        )
        total_chars += len(numbered)
    return documents


def extract_source_prompt_assets(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    candidates = sorted(
        (
            path
            for path in files
            if path.suffix.lower() in {".go", ".py", ".ts", ".tsx", ".js", ".jsx"}
            and not path.name.lower().endswith(("_test.go", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
            and "tests" not in {part.lower() for part in path.relative_to(root).parts}
        ),
        key=lambda path: (
            0 if "prompt" in path.as_posix().lower() else 1,
            0 if any(term in path.as_posix().lower() for term in ("interpreter", "worker", "compiler")) else 1,
            path.as_posix(),
        ),
    )
    assets: list[dict[str, Any]] = []
    seen: set[str] = set()
    generic_patterns = [
        re.compile(r'"""(?P<content>.{80,50000}?)"""', re.DOTALL),
        re.compile(r"'''(?P<content>.{80,50000}?)'''", re.DOTALL),
        re.compile(r"(?:=|return)\s*`(?P<content>[^`]{80,50000})`", re.DOTALL),
    ]
    go_pattern = re.compile(
        r"(?:const\s+(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*|(?:fmt\.)?Sprintf\()"
        r"`(?P<content>[^`]{80,50000})`",
        re.DOTALL,
    )
    content_markers = ("you are", "return one", "必须遵守", "输出格式", "只用口语", "json fields")

    for path in candidates:
        source = path.read_text(encoding="utf-8", errors="replace")
        patterns = [go_pattern] if path.suffix.lower() == ".go" else generic_patterns
        for pattern in patterns:
            for match in pattern.finditer(source):
                content = match.group("content").strip()
                prefix = source[max(0, match.start() - 320) : match.start()]
                if not (
                    "prompt" in path.name.lower()
                    or
                    any(term in prefix.lower() for term in PROMPT_CONTEXT_TERMS)
                    or any(marker in content.lower() for marker in content_markers)
                ):
                    continue
                fingerprint = re.sub(r"\s+", " ", content)
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                captured_identifier = match.groupdict().get("identifier")
                identifiers = re.findall(r"(?:const|var)\s+([A-Za-z_][A-Za-z0-9_]*)", prefix)
                functions = re.findall(r"func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)", source[: match.start()])
                name = captured_identifier or (identifiers[-1] if identifiers else (functions[-1] if functions else "Source Prompt"))
                start_line = source.count("\n", 0, match.start("content")) + 1
                end_line = start_line + content.count("\n")
                stored = content[:30_000]
                assets.append(
                    {
                        "id": f"prompt-{len(assets) + 1}",
                        "name": name,
                        "source_path": path.relative_to(root).as_posix(),
                        "start_line": start_line,
                        "end_line": end_line,
                        "content": stored,
                        "truncated": len(stored) < len(content),
                        "evidence_kind": "source_prompt",
                    }
                )
                if len(assets) >= 14:
                    return assets
    return assets


def extract_prompt_assets(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    assets = extract_source_prompt_assets(root, files)
    markdown = sorted(
        (path for path in files if path.suffix.lower() == ".md"),
        key=lambda path: document_rank(path.relative_to(root).as_posix()),
    )
    seen = {re.sub(r"\s+", " ", asset["content"]) for asset in assets}

    for path in markdown:
        relative = path.relative_to(root).as_posix()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        index = 0
        while index < len(lines):
            if not lines[index].lstrip().startswith("```"):
                index += 1
                continue
            end = index + 1
            while end < len(lines) and not lines[end].lstrip().startswith("```"):
                end += 1
            context = "\n".join(lines[max(0, index - 8) : index]).lower()
            content = "\n".join(lines[index + 1 : end]).strip()
            if (
                any(term in context for term in PROMPT_CONTEXT_TERMS)
                and 30 <= len(content) <= 8_000
                and re.sub(r"\s+", " ", content) not in seen
            ):
                heading = next(
                    (line.lstrip("# ").strip() for line in reversed(lines[:index]) if line.startswith("#")),
                    "Prompt",
                )
                seen.add(re.sub(r"\s+", " ", content))
                assets.append(
                    {
                        "id": f"prompt-{len(assets) + 1}",
                        "name": heading,
                        "source_path": relative,
                        "start_line": index + 2,
                        "end_line": end,
                        "content": content[:2_000],
                        "truncated": len(content) > 2_000,
                        "evidence_kind": "documented_prompt",
                    }
                )
                if len(assets) >= 18:
                    return assets
            index = end + 1
    return assets


def graph_facts(database: Path, repo_id: str) -> dict[str, Any]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT id, type, name, file_path FROM code_node WHERE repo_id = ? AND file_path IS NOT NULL",
        (repo_id,),
    ).fetchall()
    node_module: dict[str, str] = {}
    node_info: dict[str, dict[str, str]] = {}
    stats: dict[str, Counter[str]] = defaultdict(Counter)
    symbols: dict[str, list[dict[str, str]]] = defaultdict(list)
    files: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        file_path = str(row["file_path"]).replace("\\", "/")
        module = file_path.split("/", 1)[0]
        node_module[str(row["id"])] = module
        node_info[str(row["id"])] = {
            "name": str(row["name"]),
            "type": str(row["type"]),
            "path": file_path,
        }
        stats[module][str(row["type"])] += 1
        files[module].add(file_path)
        if row["type"] in {"endpoint", "function", "method", "class", "interface"}:
            symbols[module].append(
                {"name": str(row["name"]), "type": str(row["type"]), "path": file_path}
            )

    scored_modules = sorted(
        stats,
        key=lambda module: (
            module.lower() in NON_RUNTIME_TOP_LEVEL,
            -sum(stats[module].values()),
            module,
        ),
    )
    selected = [module for module in scored_modules if module.lower() not in NON_RUNTIME_TOP_LEVEL][:14]
    selected_set = set(selected)

    cross_edges: Counter[tuple[str, str, str]] = Counter()
    internal_edges: dict[str, Counter[tuple[str, str, str, str, str]]] = defaultdict(Counter)
    for row in connection.execute(
        "SELECT source_id, target_id, type FROM code_edge WHERE repo_id = ? AND type != 'contains'",
        (repo_id,),
    ):
        source = node_module.get(str(row["source_id"]))
        target = node_module.get(str(row["target_id"]))
        if source and target and source != target and source in selected_set and target in selected_set:
            cross_edges[(source, target, str(row["type"]))] += 1
        elif source and source == target and source in selected_set and str(row["type"]) == "calls":
            source_info = node_info.get(str(row["source_id"]), {})
            target_info = node_info.get(str(row["target_id"]), {})
            internal_edges[source][
                (
                    source_info.get("name", str(row["source_id"])),
                    target_info.get("name", str(row["target_id"])),
                    "calls",
                    source_info.get("path", ""),
                    target_info.get("path", ""),
                )
            ] += 1

    communities = [
        {
            "name": str(row["name"]),
            "level": int(row["level"]),
            "summary": str(row["summary"] or "")[:1_200],
        }
        for row in connection.execute(
            "SELECT name, level, summary FROM graph_community WHERE repo_id = ? "
            "AND summary IS NOT NULL ORDER BY rank DESC LIMIT 10",
            (repo_id,),
        )
    ]
    connection.close()
    return {
        "module_candidates": [
            {
                "path": module,
                "files": len(files[module]),
                "node_types": dict(stats[module].most_common()),
                "representative_symbols": sorted(
                    symbols[module], key=lambda item: (item["path"], item["type"], item["name"])
                )[:18],
                "internal_relationships": [
                    {
                        "from": source_name,
                        "to": target_name,
                        "type": edge_type,
                        "from_path": source_path,
                        "to_path": target_path,
                        "weight": count,
                    }
                    for (source_name, target_name, edge_type, source_path, target_path), count
                    in internal_edges[module].most_common(8)
                ],
            }
            for module in selected
        ],
        "cross_module_edges": [
            {"from": source, "to": target, "type": edge_type, "weight": count}
            for (source, target, edge_type), count in cross_edges.most_common(40)
        ],
        "community_summaries": communities,
    }


def synthesis_messages(
    repository_name: str,
    language: str,
    facts: dict[str, Any],
    documents: list[dict[str, Any]],
    prompt_assets: list[dict[str, Any]],
) -> list[dict[str, str]]:
    system = """You create a concise, diagram-first map of a software product.
The repository may contain ordinary application code, background workflows, data
pipelines, or LLM components. Return JSON only. Product managers must understand
the runtime behavior in under five minutes, then drill into modules and nodes.
Translate implementation vocabulary into product concepts without inventing facts.
Do not write a wiki or long prose.

Required JSON shape:
{
  "system": {"name": "...", "summary": "1-2 sentences"},
  "modules": [
    {"id": "stable-kebab-id", "name": "...", "responsibility": "one sentence", "source_paths": ["..."]}
  ],
  "nodes": [
    {"id": "stable-kebab-id", "module_id": "...", "name": "...",
     "kind": "entry|stage|llm|tool|store|artifact|output",
     "purpose": "one sentence", "inputs": ["..."], "outputs": ["..."],
     "implementation": ["path"], "prompt_ids": ["prompt-1"]}
  ],
  "edges": [
    {"from": "node-id", "to": "node-id", "type": "calls|reads|writes|produces|routes", "label": "short"}
  ]
}

Rules:
- Use 4-8 modules and no more than 30 nodes total.
- Name modules by product capability or runtime responsibility, never by folder or framework name alone.
- The system diagram must show the primary runtime path, not directory structure.
- Each module should normally contain 2-6 important runtime nodes.
- Preserve every entry, exit, branch, join, async dispatch, state write, and user-visible output before spending nodes on linear implementation detail.
- Collapse unimportant linear implementation steps into one named stage instead of deleting branch or interface semantics.
- Every node must have clear inputs and outputs.
- Every node in a multi-node module must participate in an internal or cross-module edge.
- Include cross-module edges for both requests/tasks and results/writebacks; a module's interface must be reconstructable from the edges.
- Edge labels must name the command, artifact, state, or decision being transferred. Avoid generic labels such as "calls", "task", or "result" when evidence provides a concrete name.
- Use artifact nodes when an intermediate durable document, patch, decision, queue item, or user-visible output is important to understanding the flow.
- Attach prompt_ids only to nodes that actually call an LLM or assemble a prompt.
- prompt_ids must refer exactly to supplied prompt assets; never invent prompt text.
- Non-LLM nodes must have an empty prompt_ids list.
- Prefer architecture documents over inferred code edges when they explicitly identify the active path.
- Exclude tests, prototypes, old plans, examples, and reference applications unless explicitly active.
- source_paths and implementation paths must come from supplied evidence.
- Use short names and descriptions in the requested language.
"""
    payload = {
        "repository": repository_name,
        "output_language": language,
        "code_graph": facts,
        "architecture_documents": documents,
        "prompt_assets": [
            {key: value for key, value in asset.items() if key != "content"}
            | {"content_preview": asset["content"][:1_200]}
            for asset in prompt_assets
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def synthesize_map(
    *,
    url: str,
    key: str,
    model: str,
    repository_name: str,
    language: str,
    facts: dict[str, Any],
    documents: list[dict[str, Any]],
    prompt_assets: list[dict[str, Any]],
) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(base_url=url, api_key=key, timeout=600.0, max_retries=0)
    request: dict[str, Any] = {
        "model": model,
        "messages": synthesis_messages(repository_name, language, facts, documents, prompt_assets),
        "response_format": {"type": "json_object"},
        "max_tokens": 8_000,
        "temperature": 0,
    }
    if urlparse(url).netloc.endswith("volces.com"):
        request["extra_body"] = {"thinking": {"type": "disabled"}}
    response = client.chat.completions.create(**request)
    content = response.choices[0].message.content or ""
    if not content.strip():
        raise RuntimeError(
            "LLM returned no final content "
            f"(finish_reason={response.choices[0].finish_reason}, usage={response.usage})"
        )
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "LLM did not return valid JSON "
            f"(finish_reason={response.choices[0].finish_reason}, content_length={len(content)})"
        ) from error


def safe_id(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return normalized or fallback


def normalize_map(raw: dict[str, Any], prompt_assets: list[dict[str, Any]]) -> dict[str, Any]:
    raw_modules = list(raw.get("modules") or [])
    raw_nodes = list(raw.get("nodes") or [])
    raw_edges = list(raw.get("edges") or [])
    modules: list[dict[str, Any]] = []
    module_ids: set[str] = set()
    module_aliases: dict[str, str] = {}
    for index, item in enumerate(raw_modules[:8], start=1):
        raw_module_id = str(item.get("id") or item.get("name") or "")
        module_id = safe_id(raw_module_id, f"module-{index}")
        if module_id in module_ids:
            module_id = f"{module_id}-{index}"
        module_ids.add(module_id)
        module_aliases[raw_module_id] = module_id
        module_aliases[module_id] = module_id
        modules.append(
            {
                "id": module_id,
                "name": str(item.get("name") or module_id),
                "responsibility": str(item.get("responsibility") or "")[:400],
                "source_paths": [str(path) for path in list(item.get("source_paths") or [])[:8]],
            }
        )

    assets = {asset["id"]: asset for asset in prompt_assets}
    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    node_aliases: dict[str, str] = {}
    allowed_kinds = {"entry", "stage", "llm", "tool", "store", "artifact", "output"}
    for index, item in enumerate(raw_nodes[:30], start=1):
        module_id = module_aliases.get(str(item.get("module_id") or ""), "")
        if module_id not in module_ids:
            continue
        raw_node_id = str(item.get("id") or item.get("name") or "")
        node_id = safe_id(raw_node_id, f"node-{index}")
        if node_id in node_ids:
            node_id = f"{node_id}-{index}"
        node_ids.add(node_id)
        node_aliases[raw_node_id] = node_id
        node_aliases[node_id] = node_id
        kind = str(item.get("kind") or "stage").lower()
        prompt_ids = [pid for pid in list(item.get("prompt_ids") or []) if pid in assets][:4]
        nodes.append(
            {
                "id": node_id,
                "module_id": module_id,
                "name": str(item.get("name") or node_id),
                "kind": kind if kind in allowed_kinds else "stage",
                "purpose": str(item.get("purpose") or "")[:500],
                "inputs": [str(value) for value in list(item.get("inputs") or [])[:10]],
                "outputs": [str(value) for value in list(item.get("outputs") or [])[:10]],
                "implementation": [str(value) for value in list(item.get("implementation") or [])[:8]],
                "prompts": [assets[pid] for pid in prompt_ids],
            }
        )

    edges = []
    for item in raw_edges[:80]:
        source = node_aliases.get(str(item.get("from") or ""), "")
        target = node_aliases.get(str(item.get("to") or ""), "")
        if source not in node_ids or target not in node_ids or source == target:
            continue
        edges.append(
            {
                "from": source,
                "to": target,
                "type": str(item.get("type") or "calls")[:30],
                "label": str(item.get("label") or "")[:80],
            }
        )

    system = raw.get("system") if isinstance(raw.get("system"), dict) else {}
    return enrich_system_map({
        "schema_version": "1.0",
        "system": {
            "name": str(system.get("name") or "AI System"),
            "summary": str(system.get("summary") or "")[:800],
        },
        "modules": modules,
        "nodes": nodes,
        "edges": edges,
        "diagnostics": {
            "input_module_count": len(raw_modules),
            "input_node_count": len(raw_nodes),
            "input_edge_count": len(raw_edges),
            "dropped_module_count": max(0, len(raw_modules) - len(modules)),
            "dropped_node_count": max(0, len(raw_nodes) - len(nodes)),
            "dropped_edge_count": max(0, len(raw_edges) - len(edges)),
        },
    })


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


def render_diagrams(system_map: dict[str, Any], node: str, script: Path) -> dict[str, str]:
    diagrams = {"system": system_dot(system_map)}
    for module in system_map["modules"]:
        diagrams[f'module:{module["id"]}'] = module_dot(system_map, module["id"])
    with tempfile.TemporaryDirectory(prefix="codebase-map-") as temp_directory:
        source = Path(temp_directory) / "diagrams.json"
        target = Path(temp_directory) / "rendered.json"
        source.write_text(json.dumps(diagrams, ensure_ascii=False), encoding="utf-8")
        subprocess.run([node, str(script), str(source), str(target)], check=True)
        return json.loads(target.read_text(encoding="utf-8"))


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


def html_output(system_map: dict[str, Any], diagrams: dict[str, str]) -> str:
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
<div class="diagram module-diagram">{diagrams.get('module:' + module['id'], '')}</div>
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
<header class="top"><span class="eyebrow">LIVING AI SYSTEM MAP</span><h1>{html.escape(system_map["system"]["name"])}</h1><p>{html.escape(system_map["system"]["summary"])}</p></header>
<div class="sticky"><nav class="nav"><a href="#overview">系统总览</a>{navigation}</nav></div>
<main><section class="overview" id="overview"><span class="eyebrow">SYSTEM FLOW</span><h2>整体架构</h2><p>实线表示主调用路径；虚线表示读取、写入、返回或慢任务关系。点击模块可下钻。</p><div class="diagram">{diagrams.get("system", "")}</div><div class="overview-modules">{overview_legend}</div></section>{''.join(modules_html)}</main>
<script type="application/json" id="system-map-data">{map_json}</script>
</body></html>'''


def generate_repository_map(
    *,
    repo_id: str,
    repository: Path,
    output_directory: Path,
    database: Path,
    config: Path,
    language: str = "zh",
    node: str = "node",
    dry_run: bool = False,
) -> dict[str, Any] | None:
    """Generate all three artifacts from an already analyzed CodeWiki repository."""
    root = repository.resolve()
    output = output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    files = repository_files(root)
    documents = load_evidence_documents(root, files)
    prompts = extract_prompt_assets(root, files)
    facts = graph_facts(database.resolve(), repo_id)
    url, key, model = read_api_config(config.resolve())
    print(
        f"Evidence: {len(documents)} architecture documents, {len(prompts)} prompt assets, "
        f"{len(facts['module_candidates'])} code modules",
        flush=True,
    )
    request_chars = len(synthesis_messages(root.name, language, facts, documents, prompts)[1]["content"])
    source_prompts = sum(prompt["evidence_kind"] == "source_prompt" for prompt in prompts)
    print(
        f"Synthesis input: {request_chars:,} characters; "
        f"source prompts={source_prompts}, documented prompts={len(prompts) - source_prompts}",
        flush=True,
    )
    if dry_run:
        return None
    raw = synthesize_map(
        url=url,
        key=key,
        model=model,
        repository_name=root.name,
        language=language,
        facts=facts,
        documents=documents,
        prompt_assets=prompts,
    )
    system_map = normalize_map(raw, prompts)
    diagrams = render_diagrams(
        system_map,
        node,
        Path(__file__).parent / "assets" / "render-dot.mjs",
    )
    (output / "system-map.json").write_text(
        json.dumps(system_map, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "system-map.md").write_text(markdown_output(system_map), encoding="utf-8")
    (output / "system-map.html").write_text(html_output(system_map, diagrams), encoding="utf-8")
    print(
        f"Map generated: {len(system_map['modules'])} modules, {len(system_map['nodes'])} nodes, "
        f"{sum(len(node['prompts']) for node in system_map['nodes'])} attached prompts",
        flush=True,
    )
    quality = system_map["quality"]
    print(
        f"Structure quality: {quality['status']}; edge coverage="
        f"{quality['metrics']['edge_coverage']:.0%}; warnings={len(quality['warnings'])}",
        flush=True,
    )
    return system_map


def main() -> int:
    args = parse_args()
    generate_repository_map(
        repo_id=args.repo_id,
        repository=Path(args.repository),
        output_directory=Path(args.output_directory),
        database=Path(args.database),
        config=Path(args.config),
        language=args.language,
        node=args.node,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
