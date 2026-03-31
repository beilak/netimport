"""Ranking helpers for dependency summary tables and payloads."""

from collections.abc import Sequence

from netimport_lib.summary_builder_constants import _SummaryText
from netimport_lib.summary_builder_models import _ProjectNodeSummary
from netimport_lib.summary_builder_tables import _format_table


def _format_project_ranking(project_entries: Sequence[_ProjectNodeSummary]) -> list[str]:
    return _format_table(
        (_SummaryText.rank_label, "File", "Incoming", "Outgoing", "Total"),
        [
            (
                str(index),
                entry.display_name,
                str(entry.incoming),
                str(entry.outgoing),
                str(entry.total),
            )
            for index, entry in enumerate(
                project_entries[: _SummaryText.top_items_limit],
                start=1,
            )
        ],
    )


def _build_ranked_project_files(
    project_entries: Sequence[_ProjectNodeSummary],
) -> list[dict[str, object]]:
    return [
        {
            "rank": index,
            "file": entry.display_name,
            "incoming": entry.incoming,
            "outgoing": entry.outgoing,
            "total": entry.total,
        }
        for index, entry in enumerate(
            project_entries[: _SummaryText.top_items_limit],
            start=1,
        )
    ]
