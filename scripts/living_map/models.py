"""Typed values exchanged across the system-map generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

SystemMap: TypeAlias = dict[str, Any]

@dataclass(frozen=True)
class ApiConfig:
    url: str
    key: str
    model: str

@dataclass(frozen=True)
class EvidenceBundle:
    repository_name: str
    facts: dict[str, Any]
    documents: tuple[dict[str, Any], ...]
    prompt_assets: tuple[dict[str, Any], ...]

@dataclass(frozen=True)
class ArtifactSet:
    html: Path
    markdown: Path
    data: Path

