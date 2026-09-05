"""Derive explicit module views from a normalized system graph.

The public interface is deliberately small: ``enrich_system_map`` adds every
derived view and its quality report, while ``module_view_for`` supports legacy
maps that have not yet been enriched.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import networkx as nx


PRIMARY_EDGE_TYPES = {"calls", "routes"}


def _node_indexes(system_map: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    nodes = {node["id"]: node for node in system_map.get("nodes", [])}
    modules = {node_id: node["module_id"] for node_id, node in nodes.items()}
    return nodes, modules


def module_edges(system_map: dict[str, Any]) -> list[tuple[str, str]]:
    """Return unique directed module-to-module relationships."""
    _, node_module = _node_indexes(system_map)
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for edge in system_map.get("edges", []):
        source = node_module.get(edge["from"])
        target = node_module.get(edge["to"])
        pair = (source, target)
        if source and target and source != target and pair not in seen:
            seen.add(pair)
            result.append(pair)
    return result


def module_edge_details(system_map: dict[str, Any]) -> list[dict[str, Any]]:
    """Collapse node edges into semantic module relationships."""
    _, node_module = _node_indexes(system_map)
    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    for edge in system_map.get("edges", []):
        source = node_module.get(edge["from"])
        target = node_module.get(edge["to"])
        if source and target and source != target:
            grouped[(source, target)].add(edge["type"])
    return [
        {
            "from": source,
            "to": target,
            "primary": bool(types & PRIMARY_EDGE_TYPES),
            "edge_types": sorted(types),
        }
        for (source, target), types in grouped.items()
    ]


def _group_interfaces(edges: list[dict[str, Any]], external_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        grouped[edge[external_key]].append(dict(edge))
    return [
        {"external_node_id": external_node_id, "connections": connections}
        for external_node_id, connections in grouped.items()
    ]


def _topology_kind(graph: nx.DiGraph, branch_count: int) -> str:
    if graph.number_of_nodes() <= 1:
        return "single"
    if branch_count > 1:
        return "parallel"
    if nx.is_directed_acyclic_graph(graph):
        max_in = max((degree for _, degree in graph.in_degree()), default=0)
        max_out = max((degree for _, degree in graph.out_degree()), default=0)
        if max_in <= 1 and max_out <= 1:
            return "pipeline"
        return "branched"
    return "network"


def build_module_view(system_map: dict[str, Any], module_id: str) -> dict[str, Any]:
    """Build the complete rendering view for one module, including its interface."""
    nodes, _ = _node_indexes(system_map)
    node_ids = [node["id"] for node in system_map.get("nodes", []) if node["module_id"] == module_id]
    node_set = set(node_ids)
    internal = [
        dict(edge)
        for edge in system_map.get("edges", [])
        if edge["from"] in node_set and edge["to"] in node_set
    ]
    incoming = [
        dict(edge)
        for edge in system_map.get("edges", [])
        if edge["to"] in node_set and edge["from"] not in node_set and edge["from"] in nodes
    ]
    outgoing = [
        dict(edge)
        for edge in system_map.get("edges", [])
        if edge["from"] in node_set and edge["to"] not in node_set and edge["to"] in nodes
    ]

    graph = nx.DiGraph()
    graph.add_nodes_from(node_ids)
    graph.add_edges_from((edge["from"], edge["to"]) for edge in internal)
    components = list(nx.weakly_connected_components(graph)) if node_ids else []
    order = {node_id: index for index, node_id in enumerate(node_ids)}
    components.sort(key=lambda component: min(order[node_id] for node_id in component))
    branches = []
    for index, component in enumerate(components, start=1):
        branch_nodes = sorted(component, key=order.get)
        subgraph = graph.subgraph(component)
        entries = [node_id for node_id in branch_nodes if subgraph.in_degree(node_id) == 0]
        exits = [node_id for node_id in branch_nodes if subgraph.out_degree(node_id) == 0]
        branches.append(
            {
                "id": f"{module_id}-branch-{index}",
                "node_ids": branch_nodes,
                "entry_node_ids": entries,
                "exit_node_ids": exits,
            }
        )

    connected_nodes = {
        endpoint
        for edge in internal + incoming + outgoing
        for endpoint in (edge["from"], edge["to"])
        if endpoint in node_set
    }
    orphan_node_ids = [node_id for node_id in node_ids if node_id not in connected_nodes]
    return {
        "module_id": module_id,
        "topology": _topology_kind(graph, len(branches)),
        "node_ids": node_ids,
        "branches": branches,
        "interfaces": {
            "inputs": _group_interfaces(incoming, "from"),
            "outputs": _group_interfaces(outgoing, "to"),
        },
        "internal_edges": internal,
        "metrics": {
            "node_count": len(node_ids),
            "internal_edge_count": len(internal),
            "incoming_edge_count": len(incoming),
            "outgoing_edge_count": len(outgoing),
            "branch_count": len(branches),
            "orphan_node_ids": orphan_node_ids,
        },
    }


def build_module_views(system_map: dict[str, Any]) -> list[dict[str, Any]]:
    return [build_module_view(system_map, module["id"]) for module in system_map.get("modules", [])]


def _quality_report(system_map: dict[str, Any], views: list[dict[str, Any]]) -> dict[str, Any]:
    warnings: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    diagnostics = system_map.get("diagnostics", {})
    for field, label in (
        ("dropped_module_count", "modules"),
        ("dropped_node_count", "nodes"),
        ("dropped_edge_count", "edges"),
    ):
        count = int(diagnostics.get(field, 0) or 0)
        if count:
            warnings.append(
                {"code": "normalization-drop", "module_id": "system", "message": f"Normalization dropped {count} {label}."}
            )
    represented_edges: set[tuple[str, str, str, str]] = set()
    for view in views:
        metrics = view["metrics"]
        for node_id in metrics["orphan_node_ids"]:
            errors.append(
                {"code": "orphan-node", "module_id": view["module_id"], "message": f"Node {node_id} has no visible relationship."}
            )
        if metrics["node_count"] > 1 and metrics["internal_edge_count"] == 0:
            warnings.append(
                {"code": "no-internal-flow", "module_id": view["module_id"], "message": "Module has multiple nodes but no internal flow; interface edges remain visible."}
            )
        visible = list(view["internal_edges"])
        for group in view["interfaces"]["inputs"] + view["interfaces"]["outputs"]:
            visible.extend(group["connections"])
        for edge in visible:
            represented_edges.add((edge["from"], edge["to"], edge["type"], edge["label"]))

    source_edges = {
        (edge["from"], edge["to"], edge["type"], edge["label"])
        for edge in system_map.get("edges", [])
    }
    missing_edges = source_edges - represented_edges
    errors.extend(
        {"code": "unrepresented-edge", "message": f"Edge {source}->{target} is absent from all module views."}
        for source, target, _, _ in sorted(missing_edges)
    )
    return {
        "status": "error" if errors else ("warning" if warnings else "passed"),
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "module_count": len(views),
            "node_count": len(system_map.get("nodes", [])),
            "edge_count": len(source_edges),
            "represented_edge_count": len(represented_edges),
            "edge_coverage": 1.0 if not source_edges else round(len(represented_edges) / len(source_edges), 4),
        },
    }


def enrich_system_map(system_map: dict[str, Any]) -> dict[str, Any]:
    """Add explicit module views and fail if any source edge becomes invisible."""
    result = dict(system_map)
    views = build_module_views(result)
    quality = _quality_report(result, views)
    if quality["errors"]:
        messages = "; ".join(error["message"] for error in quality["errors"])
        raise ValueError(f"Invalid module views: {messages}")
    result["schema_version"] = "1.1"
    result["module_views"] = views
    result["quality"] = quality
    return result


def module_view_for(system_map: dict[str, Any], module_id: str) -> dict[str, Any]:
    """Read an enriched view or derive one for a legacy map."""
    for view in system_map.get("module_views", []):
        if view.get("module_id") == module_id:
            return view
    return build_module_view(system_map, module_id)
