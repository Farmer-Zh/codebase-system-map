"""Compatibility entry point; prefer the installed ``repo-atlas`` command."""

from living_map.generator import main


raise SystemExit(main())
