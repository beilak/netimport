import os
from pathlib import Path

from netimport_lib.project_file_reader import find_python_files


def test_find_python_files(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    (project_root / "file1.py").touch()
    (project_root / "file2.txt").touch()

    sub_dir = project_root / "sub"
    sub_dir.mkdir()
    (sub_dir / "file3.py").touch()

    ignored_dir = project_root / "ignored"
    ignored_dir.mkdir()
    (ignored_dir / "file4.py").touch()

    py_files = find_python_files(
        project_root=str(project_root),
        ignored_dirs={"ignored"},
        ignored_files={"file5.py"},
    )

    assert len(py_files) == 2
    assert str(project_root / "file1.py") in py_files
    assert str(sub_dir / "file3.py") in py_files
