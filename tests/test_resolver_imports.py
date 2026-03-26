from pathlib import Path

import pytest

from netimport_lib.graph_builder.resolver_imports import NodeInfo, normalize_path, resolve_import_string


def _normalized_project_files(project_root: Path, *relative_paths: str) -> set[str]:
    return {normalize_path(str(project_root / relative_path)) for relative_path in relative_paths}


@pytest.mark.parametrize(
    ("import_str", "source_file", "project_files", "expected_relative_id", "expected_type"),
    [
        ("helper", "main.py", ("main.py", "helper.py"), "helper.py", "project_file"),
        ("pkg.missing_export", "main.py", ("main.py", "pkg/__init__.py"), "pkg/__init__.py", "project_file"),
        (".helper", "pkg/module.py", ("pkg/module.py", "pkg/helper.py"), "pkg/helper.py", "project_file"),
        (".service.value", "pkg/module.py", ("pkg/module.py", "pkg/service.py"), "pkg/service.py", "project_file"),
        (".", "pkg/module.py", ("pkg/module.py", "pkg/__init__.py"), "pkg/__init__.py", "project_file"),
        ("..helper", "pkg/sub/module.py", ("pkg/sub/module.py", "pkg/helper.py"), "pkg/helper.py", "project_file"),
        ("..", "pkg/sub/module.py", ("pkg/sub/module.py", "pkg/__init__.py"), "pkg/__init__.py", "project_file"),
    ],
)
def test_resolve_import_string_resolves_project_modules(
    tmp_path: Path,
    import_str: str,
    source_file: str,
    project_files: tuple[str, ...],
    expected_relative_id: str,
    expected_type: str,
) -> None:
    project_root = tmp_path / "project"

    resolved = resolve_import_string(
        import_str,
        str(project_root / source_file),
        str(project_root),
        _normalized_project_files(project_root, *project_files),
    )

    assert resolved == NodeInfo(normalize_path(str(project_root / expected_relative_id)), expected_type)


@pytest.mark.parametrize(
    ("import_str", "source_file", "project_files", "expected_type"),
    [
        (".missing.value", "pkg/module.py", ("pkg/module.py",), "unresolved_relative"),
        ("....helper", "pkg/sub/module.py", ("pkg/sub/module.py",), "unresolved_relative_too_many_dots"),
    ],
)
def test_resolve_import_string_marks_unresolved_relative_imports(
    tmp_path: Path,
    import_str: str,
    source_file: str,
    project_files: tuple[str, ...],
    expected_type: str,
) -> None:
    project_root = tmp_path / "project"

    resolved = resolve_import_string(
        import_str,
        str(project_root / source_file),
        str(project_root),
        _normalized_project_files(project_root, *project_files),
    )

    assert resolved == NodeInfo(import_str, expected_type)


def test_resolve_import_string_classifies_stdlib_imports() -> None:
    resolved = resolve_import_string("os.path", "/virtual/project/main.py", "/virtual/project", set())

    assert resolved == NodeInfo("os", "std_lib")


def test_resolve_import_string_classifies_external_imports() -> None:
    resolved = resolve_import_string("requests.sessions", "/virtual/project/main.py", "/virtual/project", set())

    assert resolved == NodeInfo("requests", "external_lib")
