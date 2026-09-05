from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codebase_map.compiler import compile_system_map  # noqa: E402
from codebase_map.document import export_system_map  # noqa: E402
from codebase_map.evidence import collect_evidence  # noqa: E402
from codebase_map.models import ApiConfig, EvidenceBundle  # noqa: E402


def raw_map() -> dict:
    return {
        "system": {"name": "Fixture", "summary": "A small test system."},
        "modules": [
            {"id": "input", "name": "Input"},
            {"id": "output", "name": "Output"},
        ],
        "nodes": [
            {"id": "request", "module_id": "input", "name": "Request", "kind": "entry"},
            {"id": "result", "module_id": "output", "name": "Result", "kind": "output"},
        ],
        "edges": [
            {"from": "request", "to": "result", "type": "produces", "label": "document"}
        ],
    }


def all_node_kinds_map() -> dict:
    kinds = ("entry", "stage", "llm", "tool", "store", "artifact", "output")
    return {
        "system": {"name": "All kinds", "summary": "Every supported node kind."},
        "modules": [{"id": "pipeline", "name": "Pipeline"}],
        "nodes": [
            {
                "id": kind,
                "module_id": "pipeline",
                "name": kind.title(),
                "kind": kind,
            }
            for kind in kinds
        ],
        "edges": [
            {
                "from": source,
                "to": target,
                "type": "calls",
                "label": "next",
            }
            for source, target in zip(kinds, kinds[1:])
        ],
    }


class PipelineModuleTests(unittest.TestCase):
    def test_compiler_accepts_a_synthesizer_at_its_internal_seam(self):
        calls: list[dict] = []

        def fake_synthesizer(**arguments):
            calls.append(arguments)
            return raw_map()

        evidence = EvidenceBundle(
            repository_name="sample",
            facts={"module_candidates": []},
            documents=(),
            prompt_assets=(),
        )
        result = compile_system_map(
            evidence,
            ApiConfig(url="https://example.invalid/v1", key="secret", model="test-model"),
            synthesizer=fake_synthesizer,
        )

        self.assertEqual("sample", calls[0]["repository_name"])
        self.assertEqual("test-model", calls[0]["model"])
        self.assertEqual("1.1", result["schema_version"])
        self.assertEqual("passed", result["quality"]["status"])

    def test_document_interface_writes_a_self_contained_primary_artifact(self):
        evidence = EvidenceBundle("sample", {}, (), ())
        system_map = compile_system_map(
            evidence,
            ApiConfig("https://example.invalid/v1", "secret", "test-model"),
            synthesizer=lambda **_: raw_map(),
        )
        with tempfile.TemporaryDirectory() as directory:
            artifacts = export_system_map(system_map, Path(directory))

            html = artifacts.html.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", html)
            self.assertIn('id="system-map-data"', html)
            self.assertIn('id="diagram-data"', html)
            self.assertIn('await import("data:text/javascript;base64," + encoded)', html)
            self.assertGreater(len(html), 1_000_000)
            self.assertIsNone(artifacts.markdown)
            self.assertIsNone(artifacts.data)
            self.assertFalse((Path(directory) / "system-map.md").exists())
            self.assertFalse((Path(directory) / "system-map.json").exists())

    def test_document_supports_every_compiler_node_kind(self):
        evidence = EvidenceBundle("sample", {}, (), ())
        system_map = compile_system_map(
            evidence,
            ApiConfig("https://example.invalid/v1", "secret", "test-model"),
            synthesizer=lambda **_: all_node_kinds_map(),
        )

        with tempfile.TemporaryDirectory() as directory:
            artifacts = export_system_map(system_map, Path(directory))

            self.assertTrue(artifacts.html.is_file())
            self.assertIn(
                "Artifact",
                artifacts.html.read_text(encoding="utf-8"),
            )

    def test_document_interface_writes_debug_artifacts_only_when_requested(self):
        evidence = EvidenceBundle("sample", {}, (), ())
        system_map = compile_system_map(
            evidence,
            ApiConfig("https://example.invalid/v1", "secret", "test-model"),
            synthesizer=lambda **_: raw_map(),
        )

        with tempfile.TemporaryDirectory() as directory:
            artifacts = export_system_map(
                system_map,
                Path(directory),
                debug_artifacts=True,
            )

            self.assertTrue(artifacts.markdown.is_file())
            self.assertEqual(
                "1.1",
                json.loads(artifacts.data.read_text(encoding="utf-8"))["schema_version"],
            )

    def test_evidence_interface_hides_repository_and_database_scanning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample"
            root.mkdir()
            (root / "README.md").write_text("# Sample\n\nArchitecture overview.", encoding="utf-8")
            (root / "prompt.py").write_text(
                'SYSTEM_PROMPT = """You are a product analyst. Return one concise JSON '
                'description of the runtime architecture using only repository evidence."""',
                encoding="utf-8",
            )
            database = Path(directory) / "codewiki.sqlite3"
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE code_node (id TEXT, repo_id TEXT, type TEXT, name TEXT, file_path TEXT);
                CREATE TABLE code_edge (repo_id TEXT, source_id TEXT, target_id TEXT, type TEXT);
                CREATE TABLE graph_community (
                    repo_id TEXT, name TEXT, level INTEGER, summary TEXT, rank REAL
                );
                INSERT INTO code_node VALUES ('a','repo','function','run','src/run.py');
                """
            )
            connection.commit()
            connection.close()

            evidence = collect_evidence(root, database, "repo")

        self.assertEqual("sample", evidence.repository_name)
        self.assertEqual("src", evidence.facts["module_candidates"][0]["path"])
        self.assertEqual("README.md", evidence.documents[0]["path"])
        self.assertEqual("source_prompt", evidence.prompt_assets[0]["evidence_kind"])


if __name__ == "__main__":
    unittest.main()
