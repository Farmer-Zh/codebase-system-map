"""Public Codebase System Map package interface."""

from __future__ import annotations

from typing import Any

__all__ = ["BuildOptions", "BuildResult", "build_repository"]
__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    if name in __all__:
        from living_map import BuildOptions, BuildResult, build_repository

        exports = {
            "BuildOptions": BuildOptions,
            "BuildResult": BuildResult,
            "build_repository": build_repository,
        }
        globals().update(exports)
        return exports[name]
    raise AttributeError(name)
