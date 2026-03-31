"""Filesystem path helpers for import resolution."""

from pathlib import Path


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


def resolve_longest_project_prefix(
    base_dir: Path,
    module_path_parts: tuple[str, ...],
    project_files_normalized: set[str],
) -> str | None:
    """Resolve the longest matching module prefix inside the project files."""
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
