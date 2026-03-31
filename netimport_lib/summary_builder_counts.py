"""Counting helpers for dependency summary graph metrics."""

import networkx as nx

from netimport_lib.summary_builder_constants import _SummaryText
from netimport_lib.summary_builder_project_nodes import _get_node_type, _iter_node_items


def _count_nodes_by_type(graph: nx.DiGraph, node_type: str) -> int:
    return sum(
        1
        for _, node_data in _iter_node_items(graph)
        if _get_node_type(node_data) == node_type
    )


def _count_unresolved_nodes(graph: nx.DiGraph) -> int:
    return sum(
        1
        for _, node_data in _iter_node_items(graph)
        if _get_node_type(node_data).startswith(_SummaryText.unresolved_prefix)
    )
