"""Project file discovery helpers."""

import os
from collections.abc import Set as AbstractSet
from pathlib import Path
from typing import Final


def find_python_files(
    project_root: str,
    *,
    ignored_dirs: AbstractSet[str],
    ignored_files: AbstractSet[str],
) -> list[str]:
    """Return Python files from a project root after applying ignore filters."""
    root_path: Final[Path] = Path(project_root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"No such path: '{project_root}'.")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: '{project_root}'.")

    python_files: list[str] = []
    for root, dirs, files in os.walk(root_path, topdown=True):
        dirs[:] = sorted(
            directory_name
            for directory_name in dirs
            if directory_name not in ignored_dirs
        )
        python_files.extend(
            str(Path(root) / file_name)
            for file_name in sorted(files)
            if file_name.endswith(".py") and file_name not in ignored_files
        )

    return python_files
