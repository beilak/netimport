"""Policy violations for CI-oriented NetImport usage."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import cast

import networkx as nx


UNRESOLVED_PREFIX = "unresolved"
EXTERNAL_LIB_NODE_TYPE = "external_lib"


@dataclass(frozen=True, slots=True)
class Violation:
    """A single policy violation discovered during analysis."""

    rule: str
    node_id: str
    label: str
    node_type: str
    message: str


def build_violations(
    graph: nx.DiGraph,
    *,
    fail_on_unresolved_imports: bool,
    forbidden_external_libs: set[str],
) -> list[Violation]:
    """Build deterministic policy violations for a dependency graph."""
    violations: list[Violation] = []

    for node_id, raw_data in sorted(graph.nodes(data=True), key=lambda item: str(item[0])):
        data = cast("Mapping[str, object]", raw_data)
        node_type = _get_str_attribute(data, "type")
        label = _get_str_attribute(data, "label", str(node_id))

        if fail_on_unresolved_imports and node_type.startswith(UNRESOLVED_PREFIX):
            violations.append(
                Violation(
                    rule="unresolved_import",
                    node_id=str(node_id),
                    label=label,
                    node_type=node_type,
                    message=f"Unresolved import detected: {label}",
                )
            )

        if node_type == EXTERNAL_LIB_NODE_TYPE and label in forbidden_external_libs:
            violations.append(
                Violation(
                    rule="forbidden_external_lib",
                    node_id=str(node_id),
                    label=label,
                    node_type=node_type,
                    message=f"Forbidden external dependency detected: {label}",
                )
            )

    return sorted(
        violations,
        key=lambda item: (item.rule, item.label, item.node_type, item.node_id),
    )


def build_violations_payload(violations: list[Violation]) -> list[dict[str, str]]:
    """Convert violations to a structured payload."""
    return [cast("dict[str, str]", asdict(violation)) for violation in violations]


def _get_str_attribute(data: Mapping[str, object], key: str, default: str = "") -> str:
    value = data.get(key, default)
    if isinstance(value, str):
        return value
    return default
