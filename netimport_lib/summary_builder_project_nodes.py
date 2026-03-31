"""Graph node extraction helpers for dependency summaries."""

import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

import networkx as nx

from netimport_lib.summary_builder_constants import NodeItem, _SummaryText
from netimport_lib.summary_builder_models import _ProjectNodeSummary


def _iter_node_items(graph: nx.DiGraph) -> Iterable[NodeItem]:
    for node_id, raw_data in graph.nodes(data=True):
        yield str(node_id), cast("Mapping[str, object]", raw_data)


def _get_str_attribute(
    node_data: Mapping[str, object],
    key: str,
    default: str = "",
) -> str:
    raw_value = node_data.get(key, default)
    if isinstance(raw_value, str):
        return raw_value
    return default


def _get_int_attribute(
    node_data: Mapping[str, object],
    key: str,
    default: int = 0,
) -> int:
    raw_value = node_data.get(key, default)
    if isinstance(raw_value, int):
        return raw_value
    return default


def _get_node_type(node_data: Mapping[str, object]) -> str:
    return _get_str_attribute(node_data, _SummaryText.type_key)


def _build_project_entries(graph: nx.DiGraph) -> list[_ProjectNodeSummary]:
    project_root = _infer_project_root(graph)
    entries: list[_ProjectNodeSummary] = []
    for node_id, node_data in _iter_node_items(graph):
        if _get_node_type(node_data) != _SummaryText.project_file_node_type:
            continue
        entries.append(
            _ProjectNodeSummary(
                node_id=node_id,
                display_name=_format_project_display_name(node_id, project_root),
                incoming=_get_int_attribute(node_data, "in_degree"),
                outgoing=_get_int_attribute(node_data, "out_degree"),
                total=_get_int_attribute(node_data, "total_degree"),
            )
        )
    return entries


def _infer_project_root(graph: nx.DiGraph) -> str | None:
    project_dirs = [
        str(Path(node_id).parent)
        for node_id, node_data in _iter_node_items(graph)
        if _get_node_type(node_data) == _SummaryText.project_file_node_type
    ]
    if not project_dirs:
        return None
    return os.path.commonpath(project_dirs)


def _format_project_display_name(node_id: str, project_root: str | None) -> str:
    if project_root is not None:
        try:
            relative_path = os.path.relpath(node_id, project_root)
        except ValueError:
            return Path(node_id).name
        if not relative_path.startswith(".."):
            return relative_path
    return Path(node_id).name
