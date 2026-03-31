"""Shared constants for dependency summary formatting."""

from collections.abc import Mapping
from typing import Final, TypeAlias


class _SummaryText:
    top_items_limit: Final[int] = 10
    project_file_node_type: Final[str] = "project_file"
    external_lib_node_type: Final[str] = "external_lib"
    unresolved_prefix: Final[str] = "unresolved"
    type_key: Final[str] = "type"
    none_text: Final[str] = "None"
    zero_text: Final[str] = "0"
    not_available_text: Final[str] = "-"
    rank_label: Final[str] = "Rank"
    project_files_analyzed_label: Final[str] = "Project files analyzed"
    summary_intro_lines: Final[tuple[str, ...]] = (
        (
            "(This report summarizes the project's import graph so a reader "
            "or LLM can spot hotspots, risky dependencies, isolated files, "
            "and missing links.)"
        ),
        (
            "(Incoming degree shows how many project files depend on a file; "
            "outgoing degree shows how many dependencies a file pulls in. "
            "Higher values usually mean higher impact or complexity.)"
        ),
    )


TableRow: TypeAlias = tuple[str, ...]
NodeItem: TypeAlias = tuple[str, Mapping[str, object]]
