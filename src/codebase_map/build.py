"""Public build interface for the installable Codebase System Map package."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .compiler import compile_system_map, load_api_config, synthesis_messages
from .document import export_system_map
from .evidence import collect_evidence
from .models import SystemMap


@dataclass(frozen=True)
class BuildOptions:
    output_directory: Path | None = None
    config: Path = Path(".env")
    work_directory: Path = Path(".codebase-map")
    language: str = "zh"
    force_analysis: bool = False
    dry_run: bool = False
    debug_artifacts: bool = False


@dataclass(frozen=True)
class BuildResult:
    repository_id: str
    output_directory: Path
    html: Path
    markdown: Path | None
    data: Path | None
    quality: dict | None


def _executable(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    suffix = ".exe" if os.name == "nt" else ""
    sibling = Path(sys.executable).with_name(name + suffix)
    if sibling.is_file():
        return str(sibling)
    raise RuntimeError(f"Required command not found: {name}")


def _run_json(command: list[str], *, cwd: Path, environment: dict[str, str]) -> dict:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command[:2])}\n{detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Command did not return JSON: {' '.join(command[:2])}") from error


def _generate_system_map(
    *,
    repo_id: str,
    repository: Path,
    output_directory: Path,
    database: Path,
    config: Path,
    language: str,
    dry_run: bool,
    debug_artifacts: bool,
) -> SystemMap | None:
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
    export_system_map(
        system_map,
        output_directory,
        debug_artifacts=debug_artifacts,
    )
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


def build_repository(repository: str | Path, options: BuildOptions | None = None) -> BuildResult:
    """Analyze one repository and write its product-readable system map."""
    options = options or BuildOptions()
    root = Path(repository).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Repository path is not a directory: {root}")
    config = options.config.expanduser().resolve()
    if not config.is_file():
        raise ValueError(f"API configuration not found: {config}")

    work = options.work_directory.expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", root.name).strip("-.") or "repository"
    output = (
        options.output_directory.expanduser().resolve()
        if options.output_directory
        else (Path.cwd() / "generated" / safe_name).resolve()
    )
    output.mkdir(parents=True, exist_ok=True)
    database = work / "codewiki.sqlite3"

    codewiki = _executable("codewiki")
    environment = dict(os.environ)
    environment["CODEWIKI_DATABASE_URL"] = f"sqlite+aiosqlite:///{database.as_posix()}"

    print("[1/3] Registering repository", flush=True)
    registration = _run_json(
        [codewiki, "repos", "add", str(root), "--name", safe_name, "--json"],
        cwd=work,
        environment=environment,
    )
    repo_id = str(registration.get("id") or "")
    if not repo_id:
        raise RuntimeError("CodeWiki did not return a repository ID.")

    print("[2/3] Analyzing code graph", flush=True)
    analyze = [codewiki, "analyze", repo_id, "--progress"]
    if options.force_analysis:
        analyze.append("--force")
    subprocess.run(analyze, cwd=work, env=environment, check=True)

    print("[3/3] Building product-readable system map", flush=True)
    system_map = _generate_system_map(
        repo_id=repo_id,
        repository=root,
        output_directory=output,
        database=database,
        config=config,
        language=options.language,
        dry_run=options.dry_run,
        debug_artifacts=options.debug_artifacts,
    )
    return BuildResult(
        repository_id=repo_id,
        output_directory=output,
        html=output / "system-map.html",
        markdown=(output / "system-map.md") if options.debug_artifacts else None,
        data=(output / "system-map.json") if options.debug_artifacts else None,
        quality=system_map.get("quality") if system_map else None,
    )
