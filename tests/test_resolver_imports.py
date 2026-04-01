from dataclasses import dataclass
from pathlib import Path

import pytest

from netimport_lib.graph_builder.resolver_imports import resolve_import_string
from netimport_lib.graph_builder.resolver_paths import normalize_path
from netimport_lib.graph_builder.resolver_shared import NodeInfo, NodeType


MAIN_FILE = "main.py"
PROJECT_FILE_TYPE: NodeType = "project_file"
PACKAGE_INIT_FILE = "pkg/__init__.py"
PACKAGE_MODULE_FILE = "pkg/module.py"
PACKAGE_HELPER_FILE = "pkg/helper.py"
SUBPACKAGE_MODULE_FILE = "pkg/sub/module.py"


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
            source_file=MAIN_FILE,
            project_files=(MAIN_FILE, "helper.py"),
            expected_relative_id="helper.py",
            expected_type=PROJECT_FILE_TYPE,
        ),
        _ProjectResolutionCase(
            import_str="pkg.missing_export",
            source_file=MAIN_FILE,
            project_files=(MAIN_FILE, PACKAGE_INIT_FILE),
            expected_relative_id=PACKAGE_INIT_FILE,
            expected_type=PROJECT_FILE_TYPE,
        ),
        _ProjectResolutionCase(
            import_str=".helper",
            source_file=PACKAGE_MODULE_FILE,
            project_files=(PACKAGE_MODULE_FILE, PACKAGE_HELPER_FILE),
            expected_relative_id=PACKAGE_HELPER_FILE,
            expected_type=PROJECT_FILE_TYPE,
        ),
        _ProjectResolutionCase(
            import_str=".service.value",
            source_file=PACKAGE_MODULE_FILE,
            project_files=(PACKAGE_MODULE_FILE, "pkg/service.py"),
            expected_relative_id="pkg/service.py",
            expected_type=PROJECT_FILE_TYPE,
        ),
        _ProjectResolutionCase(
            import_str=".",
            source_file=PACKAGE_MODULE_FILE,
            project_files=(PACKAGE_MODULE_FILE, PACKAGE_INIT_FILE),
            expected_relative_id=PACKAGE_INIT_FILE,
            expected_type=PROJECT_FILE_TYPE,
        ),
        _ProjectResolutionCase(
            import_str="..helper",
            source_file=SUBPACKAGE_MODULE_FILE,
            project_files=(SUBPACKAGE_MODULE_FILE, PACKAGE_HELPER_FILE),
            expected_relative_id=PACKAGE_HELPER_FILE,
            expected_type=PROJECT_FILE_TYPE,
        ),
        _ProjectResolutionCase(
            import_str="..",
            source_file=SUBPACKAGE_MODULE_FILE,
            project_files=(SUBPACKAGE_MODULE_FILE, PACKAGE_INIT_FILE),
            expected_relative_id=PACKAGE_INIT_FILE,
            expected_type=PROJECT_FILE_TYPE,
        ),
        _ProjectResolutionCase(
            import_str="project.pkg.module.ClassName",
            source_file=MAIN_FILE,
            project_files=(MAIN_FILE, PACKAGE_MODULE_FILE),
            expected_relative_id=PACKAGE_MODULE_FILE,
            expected_type=PROJECT_FILE_TYPE,
        ),
        _ProjectResolutionCase(
            import_str="project",
            source_file=MAIN_FILE,
            project_files=(MAIN_FILE, "__init__.py"),
            expected_relative_id="__init__.py",
            expected_type=PROJECT_FILE_TYPE,
        ),
    ],
)
def test_resolve_project_modules(
    tmp_path: Path,
    case: _ProjectResolutionCase,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

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
            source_file=PACKAGE_MODULE_FILE,
            project_files=(PACKAGE_MODULE_FILE,),
            expected_type="unresolved_relative",
        ),
        _UnresolvedResolutionCase(
            import_str="....helper",
            source_file=SUBPACKAGE_MODULE_FILE,
            project_files=(SUBPACKAGE_MODULE_FILE,),
            expected_type="unresolved_relative_too_many_dots",
        ),
    ],
)
def test_mark_unresolved_relative_imports(
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


def test_classify_stdlib_imports() -> None:
    resolved = resolve_import_string(
        "os.path",
        "/virtual/project/main.py",
        "/virtual/project",
        set(),
    )

    assert resolved == NodeInfo("os", "std_lib")


def test_classify_external_imports() -> None:
    resolved = resolve_import_string(
        "requests.sessions",
        "/virtual/project/main.py",
        "/virtual/project",
        set(),
    )

    assert resolved == NodeInfo("requests", "external_lib")
