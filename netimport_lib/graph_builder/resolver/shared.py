"""Shared types and constants for import resolution."""

import sys
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias


NodeType: TypeAlias = Literal[
    "project_file",
    "std_lib",
    "external_lib",
    "unresolved",
    "unresolved_relative",
    "unresolved_relative_internal_error",
    "unresolved_relative_too_many_dots",
]


class NodeTypes:
    """Canonical node-type labels used across graph construction helpers."""

    project_file: Final[NodeType] = "project_file"
    standard_library: Final[NodeType] = "std_lib"
    external_library: Final[NodeType] = "external_lib"
    unresolved: Final[NodeType] = "unresolved"
    unresolved_relative: Final[NodeType] = "unresolved_relative"
    unresolved_relative_internal_error: Final[NodeType] = "unresolved_relative_internal_error"
    unresolved_relative_too_many_dots: Final[NodeType] = "unresolved_relative_too_many_dots"


def _get_standard_library_modules() -> frozenset[str]:
    if hasattr(sys, "stdlib_module_names"):
        return frozenset(sys.stdlib_module_names)
    return frozenset()


STANDARD_LIB_MODULES: Final[frozenset[str]] = _get_standard_library_modules()


@dataclass(frozen=True, slots=True)
class NodeInfo:
    """Resolved graph node metadata for an import string."""

    id: str
    type: NodeType
