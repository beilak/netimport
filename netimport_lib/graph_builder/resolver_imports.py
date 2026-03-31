"""Import string resolution for dependency graph nodes."""

import sys
from dataclasses import dataclass
from pathlib import Path
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


def normalize_path(path: str, project_root: str | None = None) -> str:
    """Normalize a path and optionally make it relative to a project root."""
    abs_path = Path(path).resolve()
    if project_root is not None:
        abs_project_root = Path(project_root).resolve()
        try:
            return str(abs_path.relative_to(abs_project_root))
        except ValueError:
            return str(abs_path)

    return str(abs_path)


def _resolve_existing_path(candidate_path: Path, project_files_normalized: set[str]) -> str | None:
    normalized_candidate = normalize_path(str(candidate_path))
    if normalized_candidate in project_files_normalized:
        return normalized_candidate
    return None


def _resolve_module_from_base(
    base_dir: Path,
    module_path_parts: tuple[str, ...],
    project_files_normalized: set[str],
) -> str | None:
    if not module_path_parts:
        return _resolve_existing_path(base_dir / "__init__.py", project_files_normalized)

    module_base = base_dir.joinpath(*module_path_parts)
    for candidate_path in (module_base.with_suffix(".py"), module_base / "__init__.py"):
        resolved_path = _resolve_existing_path(candidate_path, project_files_normalized)
        if resolved_path is not None:
            return resolved_path

    return None


def _resolve_longest_project_prefix(
    base_dir: Path,
    module_path_parts: tuple[str, ...],
    project_files_normalized: set[str],
) -> str | None:
    if not module_path_parts:
        return _resolve_module_from_base(base_dir, (), project_files_normalized)

    for prefix_length in range(len(module_path_parts), 0, -1):
        resolved_path = _resolve_module_from_base(
            base_dir,
            module_path_parts[:prefix_length],
            project_files_normalized,
        )
        if resolved_path is not None:
            return resolved_path

    return None


def _split_relative_import(import_str: str) -> tuple[int, tuple[str, ...]]:
    stripped_import = import_str.lstrip(".")
    num_dots = len(import_str) - len(stripped_import)
    if not stripped_import:
        return num_dots, ()

    return num_dots, tuple(part for part in stripped_import.split(".") if part)


def _build_relative_base_dir(
    source_file_path_normalized: str,
    project_root: str,
    num_dots: int,
) -> tuple[Path | None, NodeType | None]:
    project_root_path = Path(project_root).resolve()
    source_path = Path(source_file_path_normalized).resolve()

    try:
        source_dir_relative_to_root = source_path.relative_to(project_root_path).parent
    except ValueError:
        return None, "unresolved_relative_internal_error"

    levels_to_go_up = num_dots - 1
    if levels_to_go_up > len(source_dir_relative_to_root.parts):
        return None, "unresolved_relative_too_many_dots"

    base_dir_relative_to_root = source_dir_relative_to_root
    for _ in range(levels_to_go_up):
        base_dir_relative_to_root = base_dir_relative_to_root.parent

    return project_root_path / base_dir_relative_to_root, None


def _resolve_relative_import(
    import_str: str,
    source_file_path_normalized: str,
    project_root: str,
    project_files_normalized: set[str],
) -> NodeInfo:
    num_dots, module_path_parts = _split_relative_import(import_str)
    base_dir, error_type = _build_relative_base_dir(
        source_file_path_normalized,
        project_root,
        num_dots,
    )

    if error_type is not None:
        return NodeInfo(import_str, error_type)
    if base_dir is None:
        return NodeInfo(import_str, "unresolved_relative_internal_error")

    resolved_path = _resolve_longest_project_prefix(
        base_dir,
        module_path_parts,
        project_files_normalized,
    )
    if resolved_path is not None:
        return NodeInfo(resolved_path, "project_file")

    return NodeInfo(import_str, "unresolved_relative")


def _resolve_absolute_import(
    import_str: str,
    project_root: str,
    project_files_normalized: set[str],
) -> NodeInfo:
    project_root_path = Path(project_root).resolve()
    absolute_module_parts = tuple(part for part in import_str.split(".") if part)
    if not absolute_module_parts:
        return NodeInfo(import_str, "unresolved")

    resolved_path = _resolve_longest_project_prefix(
        project_root_path,
        absolute_module_parts,
        project_files_normalized,
    )
    if resolved_path is not None:
        return NodeInfo(resolved_path, "project_file")

    project_package_name = project_root_path.name
    if absolute_module_parts[0] == project_package_name:
        resolved_path = _resolve_longest_project_prefix(
            project_root_path,
            absolute_module_parts[1:],
            project_files_normalized,
        )
        if resolved_path is not None:
            return NodeInfo(resolved_path, "project_file")

    root_module_name = absolute_module_parts[0]
    if root_module_name in STANDARD_LIB_MODULES:
        return NodeInfo(root_module_name, "std_lib")

    return NodeInfo(root_module_name, "external_lib")


def resolve_import_string(
    import_str: str,
    source_file_path_normalized: str,
    project_root: str,
    project_files_normalized: set[str],
) -> NodeInfo:
    """Resolve an import string to a graph node."""
    if import_str.startswith("."):
        return _resolve_relative_import(
            import_str,
            source_file_path_normalized,
            project_root,
            project_files_normalized,
        )

    return _resolve_absolute_import(import_str, project_root, project_files_normalized)
