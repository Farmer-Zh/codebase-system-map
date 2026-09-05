"""Collect product and code-graph evidence behind one small interface."""

from __future__ import annotations

import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from .models import EvidenceBundle


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


def collect_evidence(repository: Path, database: Path, repo_id: str) -> EvidenceBundle:
    """Collect the bounded evidence needed to describe one analyzed repository."""
    root = repository.resolve()
    files = repository_files(root)
    return EvidenceBundle(
        repository_name=root.name,
        facts=graph_facts(database.resolve(), repo_id),
        documents=tuple(load_evidence_documents(root, files)),
        prompt_assets=tuple(extract_prompt_assets(root, files)),
    )


__all__ = ["collect_evidence"]
