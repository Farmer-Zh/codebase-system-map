from __future__ import annotations

import importlib
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from living_map.topology import enrich_system_map, module_view_for  # noqa: E402


def load_generator():
    return importlib.import_module("living_map.generator")


def parallel_fixture() -> dict:
    return {
        "schema_version": "1.0",
        "system": {"name": "Fixture", "summary": ""},
        "modules": [
            {"id": "store", "name": "Store", "responsibility": "", "source_paths": []},
            {"id": "workers", "name": "Workers", "responsibility": "", "source_paths": []},
        ],
        "nodes": [
            {"id": "commit", "module_id": "store", "name": "Commit", "kind": "store", "purpose": "", "inputs": [], "outputs": [], "implementation": [], "prompts": []},
            {"id": "alpha", "module_id": "workers", "name": "Alpha", "kind": "llm", "purpose": "", "inputs": [], "outputs": [], "implementation": [], "prompts": []},
            {"id": "beta", "module_id": "workers", "name": "Beta", "kind": "llm", "purpose": "", "inputs": [], "outputs": [], "implementation": [], "prompts": []},
            {"id": "gamma", "module_id": "workers", "name": "Gamma", "kind": "llm", "purpose": "", "inputs": [], "outputs": [], "implementation": [], "prompts": []},
        ],
        "edges": [
            {"from": "commit", "to": "alpha", "type": "produces", "label": "alpha task"},
            {"from": "commit", "to": "beta", "type": "produces", "label": "beta task"},
            {"from": "beta", "to": "gamma", "type": "calls", "label": "next"},
            {"from": "alpha", "to": "commit", "type": "writes", "label": "alpha patch"},
            {"from": "gamma", "to": "commit", "type": "writes", "label": "gamma patch"},
        ],
    }


class TopologyTests(unittest.TestCase):
    def test_orphan_node_fails_quality_gate(self):
        fixture = parallel_fixture()
        fixture["nodes"].append(
            {"id": "orphan", "module_id": "workers", "name": "Orphan", "kind": "stage", "purpose": "", "inputs": [], "outputs": [], "implementation": [], "prompts": []}
        )
        with self.assertRaisesRegex(ValueError, "orphan"):
            enrich_system_map(fixture)

    def test_parallel_view_exposes_interface_and_branches(self):
        system_map = enrich_system_map(parallel_fixture())
        view = module_view_for(system_map, "workers")
        self.assertEqual("parallel", view["topology"])
        self.assertEqual(2, view["metrics"]["branch_count"])
        self.assertEqual(1, len(view["interfaces"]["inputs"]))
        self.assertEqual(1, len(view["interfaces"]["outputs"]))
        self.assertEqual(1.0, system_map["quality"]["metrics"]["edge_coverage"])

    def test_normalization_always_builds_views_and_quality_report(self):
        generator = load_generator()
        raw = {
            "system": {"name": "Fixture", "summary": ""},
            "modules": [{"id": "one", "name": "One"}, {"id": "two", "name": "Two"}],
            "nodes": [
                {"id": "a", "module_id": "one", "name": "A", "kind": "entry"},
                {"id": "b", "module_id": "two", "name": "B", "kind": "output"},
            ],
            "edges": [{"from": "a", "to": "b", "type": "calls", "label": "request"}],
        }
        system_map = generator.normalize_map(raw, [])
        self.assertEqual("1.1", system_map["schema_version"])
        self.assertEqual(2, len(system_map["module_views"]))
        self.assertEqual("passed", system_map["quality"]["status"])

    def test_renderer_consumes_saved_module_view_not_raw_edges(self):
        generator = load_generator()
        system_map = enrich_system_map(parallel_fixture())
        system_map["edges"] = []
        dot = generator.module_dot(system_map, "workers")
        self.assertIn("alpha task", dot)
        self.assertIn("gamma patch", dot)
        self.assertGreaterEqual(dot.count(" -> "), 5)

    def test_codewiki_evidence_keeps_internal_calls(self):
        generator = load_generator()
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "codewiki.sqlite3"
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE code_node (id TEXT, repo_id TEXT, type TEXT, name TEXT, file_path TEXT);
                CREATE TABLE code_edge (repo_id TEXT, source_id TEXT, target_id TEXT, type TEXT);
                CREATE TABLE graph_community (repo_id TEXT, name TEXT, level INTEGER, summary TEXT, rank REAL);
                INSERT INTO code_node VALUES ('a','repo','function','dispatch','runtime/dispatch.py');
                INSERT INTO code_node VALUES ('b','repo','function','worker','runtime/worker.py');
                INSERT INTO code_edge VALUES ('repo','a','b','calls');
                """
            )
            connection.commit()
            connection.close()
            facts = generator.graph_facts(database, "repo")
        runtime = next(module for module in facts["module_candidates"] if module["path"] == "runtime")
        self.assertEqual("dispatch", runtime["internal_relationships"][0]["from"])
        self.assertEqual("worker", runtime["internal_relationships"][0]["to"])


if __name__ == "__main__":
    unittest.main()
