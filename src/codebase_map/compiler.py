"""Compile repository evidence into a validated product-readable system map."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import ApiConfig, EvidenceBundle, SystemMap
from .topology import enrich_system_map


def resolve_output_language(
    requested: str,
    documents: list[dict[str, Any]],
) -> str:
    """Resolve an explicit language or infer Chinese/English from project documents."""
    normalized = requested.strip().lower()
    aliases = {
        "chinese": "zh",
        "中文": "zh",
        "zh-cn": "zh",
        "english": "en",
        "英文": "en",
        "en-us": "en",
        "en-gb": "en",
    }
    if normalized and normalized != "auto":
        return aliases.get(normalized, normalized)

    text = "\n".join(str(document.get("content") or "") for document in documents)
    han_characters = len(re.findall(r"[\u3400-\u9fff]", text))
    latin_characters = len(re.findall(r"[A-Za-z]", text))
    if han_characters >= 20 and han_characters >= latin_characters * 0.2:
        return "zh"
    return "en"


def read_api_config(path: Path) -> tuple[str, str, str]:
    from dotenv import dotenv_values

    values = dotenv_values(path)
    url = str(values.get("URL") or "").strip()
    key = str(values.get("KEY") or "").strip()
    model = str(values.get("MODEL") or "").strip()
    if not all((url, key, model)):
        raise ValueError(f"Set URL, KEY and MODEL in {path}")
    return url, key, model


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


def normalize_map(
    raw: dict[str, Any],
    prompt_assets: list[dict[str, Any]],
    language: str = "en",
) -> dict[str, Any]:
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
            "language": language,
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


Synthesizer = Callable[..., dict[str, Any]]


def load_api_config(path: Path) -> ApiConfig:
    """Load the only three model settings exposed to users."""
    url, key, model = read_api_config(path.resolve())
    return ApiConfig(url=url, key=key, model=model)


def compile_system_map(
    evidence: EvidenceBundle,
    config: ApiConfig,
    language: str = "auto",
    *,
    synthesizer: Synthesizer = synthesize_map,
) -> SystemMap:
    """Synthesize, normalize, and structurally validate one system map."""
    resolved_language = resolve_output_language(language, list(evidence.documents))
    raw = synthesizer(
        url=config.url,
        key=config.key,
        model=config.model,
        repository_name=evidence.repository_name,
        language=resolved_language,
        facts=evidence.facts,
        documents=list(evidence.documents),
        prompt_assets=list(evidence.prompt_assets),
    )
    return normalize_map(raw, list(evidence.prompt_assets), resolved_language)


__all__ = ["compile_system_map", "load_api_config", "resolve_output_language"]
