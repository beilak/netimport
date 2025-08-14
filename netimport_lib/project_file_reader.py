import os
from pathlib import Path


def find_python_files(
    project_root: str,
    *,
    ignored_dirs: set[str],
    ignored_files: set[str],
) -> list[str]:
    root_path = Path(project_root).resolve()
    if not root_path.exists():
        raise ValueError(f"No '{project_root}'")
    if not root_path.is_dir():
        raise ValueError(f"No dir '{project_root}'")

    python_files: list[str] = []
    for root, dirs, files in os.walk(root_path, topdown=True):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        for file in files:
            if file.endswith(".py") and file not in ignored_files:
                file_path = Path(root) / file
                python_files.append(str(file_path))
    return python_files
