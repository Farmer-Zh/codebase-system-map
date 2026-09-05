"""Public build interface for the installable RepoAtlas package."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .generator import generate_repository_map


@dataclass(frozen=True)
class BuildOptions:
    output_directory: Path | None = None
    config: Path = Path(".env")
    work_directory: Path = Path(".repo-atlas")
    language: str = "zh"
    force_analysis: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class BuildResult:
    repository_id: str
    output_directory: Path
    html: Path
    markdown: Path
    data: Path
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
    # A dry run stops before SVG rendering, so it should not require Node.js.
    node = _executable("node") if not options.dry_run else "node"
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
    system_map = generate_repository_map(
        repo_id=repo_id,
        repository=root,
        output_directory=output,
        database=database,
        config=config,
        language=options.language,
        node=node,
        dry_run=options.dry_run,
    )
    return BuildResult(
        repository_id=repo_id,
        output_directory=output,
        html=output / "system-map.html",
        markdown=output / "system-map.md",
        data=output / "system-map.json",
        quality=system_map.get("quality") if system_map else None,
    )
