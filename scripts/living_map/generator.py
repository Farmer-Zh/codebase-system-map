"""Compatibility facade for the focused evidence, compiler, and document modules."""

from __future__ import annotations

import argparse
from pathlib import Path

from .compiler import (
    compile_system_map,
    load_api_config,
    normalize_map,
    read_api_config,
    safe_id,
    synthesize_map,
    synthesis_messages,
)
from .document import (
    chips,
    dot_escape,
    export_system_map,
    html_output,
    markdown_output,
    mermaid_id,
    mermaid_label,
    module_dot,
    render_diagrams,
    system_dot,
)
from .evidence import (
    collect_evidence,
    document_rank,
    extract_prompt_assets,
    extract_source_prompt_assets,
    graph_facts,
    load_evidence_documents,
    repository_files,
)
from .models import SystemMap

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
) -> SystemMap | None:
    """Run the evidence-to-system-model-to-document pipeline."""
    evidence = collect_evidence(repository, database, repo_id)
    print(
        f"Evidence: {len(evidence.documents)} architecture documents, "
        f"{len(evidence.prompt_assets)} prompt assets, "
        f"{len(evidence.facts['module_candidates'])} code modules",
        flush=True,
    )
    request_chars = len(
        synthesis_messages(
            evidence.repository_name,
            language,
            evidence.facts,
            list(evidence.documents),
            list(evidence.prompt_assets),
        )[1]["content"]
    )
    source_prompts = sum(
        prompt["evidence_kind"] == "source_prompt" for prompt in evidence.prompt_assets
    )
    print(
        f"Synthesis input: {request_chars:,} characters; source prompts={source_prompts}, "
        f"documented prompts={len(evidence.prompt_assets) - source_prompts}",
        flush=True,
    )
    if dry_run:
        return None

    system_map = compile_system_map(evidence, load_api_config(config), language)
    export_system_map(system_map, output_directory, node)
    print(
        f"Map generated: {len(system_map['modules'])} modules, {len(system_map['nodes'])} nodes, "
        f"{sum(len(item['prompts']) for item in system_map['nodes'])} attached prompts",
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
