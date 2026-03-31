"""List-formatting helpers for dependency summary sections."""

from collections.abc import Sequence

import networkx as nx

from netimport_lib.summary_builder_constants import TableRow, _SummaryText
from netimport_lib.summary_builder_models import _SimpleNodeSummary
from netimport_lib.summary_builder_project_nodes import (
    _get_node_type,
    _get_str_attribute,
    _iter_node_items,
)
from netimport_lib.summary_builder_tables import _format_table
from netimport_lib.violations import Violation


def _build_external_entries(graph: nx.DiGraph) -> list[_SimpleNodeSummary]:
    entries = [
        _SimpleNodeSummary(
            node_id=node_id,
            display_name=_get_str_attribute(node_data, "label", node_id),
            node_type=_get_node_type(node_data),
        )
        for node_id, node_data in _iter_node_items(graph)
        if _get_node_type(node_data) == _SummaryText.external_lib_node_type
    ]
    return sorted(entries, key=lambda entry: entry.display_name)


def _build_unresolved_entries(graph: nx.DiGraph) -> list[_SimpleNodeSummary]:
    entries = [
        _SimpleNodeSummary(
            node_id=node_id,
            display_name=_get_str_attribute(node_data, "label", node_id),
            node_type=_get_node_type(node_data),
        )
        for node_id, node_data in _iter_node_items(graph)
        if _get_node_type(node_data).startswith(_SummaryText.unresolved_prefix)
    ]
    return sorted(entries, key=lambda entry: (entry.display_name, entry.node_type))


def _format_simple_node_list(entries: Sequence[_SimpleNodeSummary]) -> list[str]:
    if not entries:
        return _format_table(("Dependency",), [(_SummaryText.none_text,)])
    return _format_table(
        (_SummaryText.rank_label, "Dependency"),
        _build_ranked_simple_rows(entries),
    )


def _format_unresolved_entries(entries: Sequence[_SimpleNodeSummary]) -> list[str]:
    if not entries:
        return _format_table(
            ("Import", "Type"),
            [(_SummaryText.none_text, _SummaryText.not_available_text)],
        )
    return _format_table(
        (_SummaryText.rank_label, "Import", "Type"),
        [
            (str(index), entry.display_name, entry.node_type)
            for index, entry in enumerate(entries, start=1)
        ],
    )


def _format_violations(violations: Sequence[Violation]) -> list[str]:
    if not violations:
        return _format_table(
            ("Rule", "Message"),
            [(_SummaryText.none_text, _SummaryText.not_available_text)],
        )
    return _format_table(
        (_SummaryText.rank_label, "Rule", "Target", "Type", "Message"),
        [
            (
                str(index),
                violation.rule,
                violation.label,
                violation.node_type,
                violation.message,
            )
            for index, violation in enumerate(violations, start=1)
        ],
    )


def _build_ranked_simple_rows(entries: Sequence[_SimpleNodeSummary]) -> list[TableRow]:
    return [
        (str(index), entry.display_name)
        for index, entry in enumerate(entries, start=1)
    ]


def _build_unresolved_import_payload(
    unresolved_entries: Sequence[_SimpleNodeSummary],
) -> list[dict[str, object]]:
    return [
        {
            "rank": index,
            "import_name": entry.display_name,
            "type": entry.node_type,
        }
        for index, entry in enumerate(unresolved_entries, start=1)
    ]
