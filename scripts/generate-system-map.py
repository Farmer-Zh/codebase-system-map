"""Compatibility entry point; prefer the installed ``codebase-map`` command."""

from living_map.generator import main


raise SystemExit(main())
