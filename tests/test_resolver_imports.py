from dataclasses import dataclass
from pathlib import Path

import pytest

from netimport_lib.graph_builder.resolver_imports import (
    NodeInfo,
    NodeType,
    normalize_path,
    resolve_import_string,
)


@dataclass(frozen=True, slots=True)
class _ProjectResolutionCase:
    import_str: str
    source_file: str
    project_files: tuple[str, ...]
    expected_relative_id: str
    expected_type: NodeType


@dataclass(frozen=True, slots=True)
class _UnresolvedResolutionCase:
    import_str: str
    source_file: str
    project_files: tuple[str, ...]
    expected_type: NodeType


def _normalized_project_files(project_root: Path, *relative_paths: str) -> set[str]:
    return {normalize_path(str(project_root / relative_path)) for relative_path in relative_paths}


@pytest.mark.parametrize(
    "case",
    [
        _ProjectResolutionCase(
            import_str="helper",
            source_file="main.py",
            project_files=("main.py", "helper.py"),
            expected_relative_id="helper.py",
            expected_type="project_file",
        ),
        _ProjectResolutionCase(
            import_str="pkg.missing_export",
            source_file="main.py",
            project_files=("main.py", "pkg/__init__.py"),
            expected_relative_id="pkg/__init__.py",
            expected_type="project_file",
        ),
        _ProjectResolutionCase(
            import_str=".helper",
            source_file="pkg/module.py",
            project_files=("pkg/module.py", "pkg/helper.py"),
            expected_relative_id="pkg/helper.py",
            expected_type="project_file",
        ),
        _ProjectResolutionCase(
            import_str=".service.value",
            source_file="pkg/module.py",
            project_files=("pkg/module.py", "pkg/service.py"),
            expected_relative_id="pkg/service.py",
            expected_type="project_file",
        ),
        _ProjectResolutionCase(
            import_str=".",
            source_file="pkg/module.py",
            project_files=("pkg/module.py", "pkg/__init__.py"),
            expected_relative_id="pkg/__init__.py",
            expected_type="project_file",
        ),
        _ProjectResolutionCase(
            import_str="..helper",
            source_file="pkg/sub/module.py",
            project_files=("pkg/sub/module.py", "pkg/helper.py"),
            expected_relative_id="pkg/helper.py",
            expected_type="project_file",
        ),
        _ProjectResolutionCase(
            import_str="..",
            source_file="pkg/sub/module.py",
            project_files=("pkg/sub/module.py", "pkg/__init__.py"),
            expected_relative_id="pkg/__init__.py",
            expected_type="project_file",
        ),
    ],
)
def test_resolve_import_string_resolves_project_modules(
    tmp_path: Path,
    case: _ProjectResolutionCase,
) -> None:
    project_root = tmp_path / "project"

    resolved = resolve_import_string(
        case.import_str,
        str(project_root / case.source_file),
        str(project_root),
        _normalized_project_files(project_root, *case.project_files),
    )

    assert resolved == NodeInfo(
        normalize_path(str(project_root / case.expected_relative_id)),
        case.expected_type,
    )


@pytest.mark.parametrize(
    "case",
    [
        _UnresolvedResolutionCase(
            import_str=".missing.value",
            source_file="pkg/module.py",
            project_files=("pkg/module.py",),
            expected_type="unresolved_relative",
        ),
        _UnresolvedResolutionCase(
            import_str="....helper",
            source_file="pkg/sub/module.py",
            project_files=("pkg/sub/module.py",),
            expected_type="unresolved_relative_too_many_dots",
        ),
    ],
)
def test_resolve_import_string_marks_unresolved_relative_imports(
    tmp_path: Path,
    case: _UnresolvedResolutionCase,
) -> None:
    project_root = tmp_path / "project"

    resolved = resolve_import_string(
        case.import_str,
        str(project_root / case.source_file),
        str(project_root),
        _normalized_project_files(project_root, *case.project_files),
    )

    assert resolved == NodeInfo(case.import_str, case.expected_type)


def test_resolve_import_string_classifies_stdlib_imports() -> None:
    resolved = resolve_import_string(
        "os.path",
        "/virtual/project/main.py",
        "/virtual/project",
        set(),
    )

    assert resolved == NodeInfo("os", "std_lib")


def test_resolve_import_string_classifies_external_imports() -> None:
    resolved = resolve_import_string(
        "requests.sessions",
        "/virtual/project/main.py",
        "/virtual/project",
        set(),
    )

    assert resolved == NodeInfo("requests", "external_lib")
