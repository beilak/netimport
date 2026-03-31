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


def _node_sort_key(node_item: tuple[object, object]) -> str:
    return str(node_item[0])


def _violation_sort_key(violation: Violation) -> tuple[str, str, str, str]:
    return (
        violation.rule,
        violation.label,
        violation.node_type,
        violation.node_id,
    )


def _collect_node_violations(
    node_id: object,
    node_data: Mapping[str, object],
    *,
    fail_on_unresolved_imports: bool,
    forbidden_external_libs: set[str],
) -> list[Violation]:
    node_type = _get_str_attribute(node_data, "type")
    label = _get_str_attribute(node_data, "label", str(node_id))
    node_violations: list[Violation] = []

    if fail_on_unresolved_imports and node_type.startswith(UNRESOLVED_PREFIX):
        node_violations.append(
            Violation(
                rule="unresolved_import",
                node_id=str(node_id),
                label=label,
                node_type=node_type,
                message=f"Unresolved import detected: {label}",
            )
        )
    if node_type == EXTERNAL_LIB_NODE_TYPE and label in forbidden_external_libs:
        node_violations.append(
            Violation(
                rule="forbidden_external_lib",
                node_id=str(node_id),
                label=label,
                node_type=node_type,
                message=f"Forbidden external dependency detected: {label}",
            )
        )
    return node_violations


def build_violations(
    graph: nx.DiGraph,
    *,
    fail_on_unresolved_imports: bool,
    forbidden_external_libs: set[str],
) -> list[Violation]:
    """Build deterministic policy violations for a dependency graph."""
    violations: list[Violation] = []

    for node_id, raw_node_data in sorted(graph.nodes(data=True), key=_node_sort_key):
        node_data = cast("Mapping[str, object]", raw_node_data)
        violations.extend(
            _collect_node_violations(
                node_id,
                node_data,
                fail_on_unresolved_imports=fail_on_unresolved_imports,
                forbidden_external_libs=forbidden_external_libs,
            )
        )

    return sorted(
        violations,
        key=_violation_sort_key,
    )


def build_violations_payload(violations: list[Violation]) -> list[dict[str, str]]:
    """Convert violations to a structured payload."""
    return [cast("dict[str, str]", asdict(violation)) for violation in violations]


def _get_str_attribute(
    node_data: Mapping[str, object],
    key: str,
    default: str = "",
) -> str:
    raw_value = node_data.get(key, default)
    if isinstance(raw_value, str):
        return raw_value
    return default
