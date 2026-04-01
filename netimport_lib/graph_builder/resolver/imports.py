"""Import string resolution for dependency graph nodes."""

from pathlib import Path

from netimport_lib.graph_builder.resolver.paths import (
    normalize_path as _shared_normalize_path,
)
from netimport_lib.graph_builder.resolver.paths import resolve_longest_project_prefix
from netimport_lib.graph_builder.resolver.shared import (
    STANDARD_LIB_MODULES,
    NodeInfo,
    NodeType,
    NodeTypes,
)


def _normalize_path(path: str, project_root: str | None = None) -> str:
    """Delegate path normalization to the shared filesystem helpers."""
    return _shared_normalize_path(path, project_root)


def normalize_path(path: str, project_root: str | None = None) -> str:
    """Keep the historical normalize_path export for resolver tests."""
    return _normalize_path(path, project_root)


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
        return None, NodeTypes.unresolved_relative_internal_error

    levels_to_go_up = num_dots - 1
    if levels_to_go_up > len(source_dir_relative_to_root.parts):
        return None, NodeTypes.unresolved_relative_too_many_dots

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
        return NodeInfo(import_str, NodeTypes.unresolved_relative_internal_error)

    resolved_path = resolve_longest_project_prefix(
        base_dir,
        module_path_parts,
        project_files_normalized,
    )
    if resolved_path is not None:
        return NodeInfo(resolved_path, NodeTypes.project_file)

    return NodeInfo(import_str, NodeTypes.unresolved_relative)


def _resolve_absolute_import(
    import_str: str,
    project_root: str,
    project_files_normalized: set[str],
) -> NodeInfo:
    project_root_path = Path(project_root).resolve()
    absolute_module_parts = tuple(part for part in import_str.split(".") if part)
    if not absolute_module_parts:
        return NodeInfo(import_str, NodeTypes.unresolved)

    resolved_path = resolve_longest_project_prefix(
        project_root_path,
        absolute_module_parts,
        project_files_normalized,
    )
    if resolved_path is not None:
        return NodeInfo(resolved_path, NodeTypes.project_file)

    project_package_name = project_root_path.name
    if absolute_module_parts[0] == project_package_name:
        resolved_path = resolve_longest_project_prefix(
            project_root_path,
            absolute_module_parts[1:],
            project_files_normalized,
        )
        if resolved_path is not None:
            return NodeInfo(resolved_path, NodeTypes.project_file)

    root_module_name = absolute_module_parts[0]
    if root_module_name in STANDARD_LIB_MODULES:
        return NodeInfo(root_module_name, NodeTypes.standard_library)

    return NodeInfo(root_module_name, NodeTypes.external_library)


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
