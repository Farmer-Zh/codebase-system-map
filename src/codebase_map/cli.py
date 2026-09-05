"""Command-line interface for Codebase System Map."""

from __future__ import annotations

import argparse
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="codebase-map", description="Turn a code repository into a product-readable system map.")
    root.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    root.add_argument("repository", help="Local repository directory")
    root.add_argument("-o", "--output", type=Path, help="Output directory (default: ./generated/<repo>)")
    root.add_argument("--config", type=Path, default=Path(".env"), help="File containing URL, KEY, and MODEL")
    root.add_argument("--work-dir", type=Path, default=Path(".codebase-map"), help="CodeWiki cache/database directory")
    root.add_argument("--language", default="zh", help="Output language (default: zh)")
    root.add_argument("--force-analysis", action="store_true", help="Discard CodeWiki's incremental analysis cache")
    root.add_argument("--dry-run", action="store_true", help="Collect and size evidence without calling the LLM")
    root.add_argument(
        "--debug-artifacts",
        action="store_true",
        help="Also write system-map.md and system-map.json",
    )
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    from .build import BuildOptions, build_repository

    result = build_repository(
        args.repository,
        BuildOptions(
            output_directory=args.output,
            config=args.config,
            work_directory=args.work_dir,
            language=args.language,
            force_analysis=args.force_analysis,
            dry_run=args.dry_run,
            debug_artifacts=args.debug_artifacts,
        ),
    )
    if args.dry_run:
        print("Dry run complete; no artifacts written.")
    else:
        print("\nSystem map generated:")
        print(f"  {result.html}")
        if result.markdown and result.data:
            print(f"Debug artifacts: {result.markdown}, {result.data}")
    return 0
