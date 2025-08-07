import os
import sys
from typing import NamedTuple


def get_standard_library_modules() -> set[str]:
    if hasattr(sys, "stdlib_module_names"):  # from Python 3.10
        return set(sys.stdlib_module_names)
    return set()


STANDARD_LIB_MODULES = get_standard_library_modules()


def normalize_path(path: str, project_root: str | None = None) -> str:
    abs_path = os.path.abspath(path)
    if project_root:
        abs_project_root = os.path.abspath(project_root)
        if abs_path.startswith(abs_project_root):
            return os.path.relpath(abs_path, abs_project_root).replace(os.sep, "/")
    return abs_path.replace(os.sep, "/")


def try_resolve_module_path(
    *,
    module_path_parts: list[str],
    project_root: str,
    project_files_normalized: set[str],
    base_path_parts_for_relative: list[str] | None = None,
) -> str | None:
    current_path_parts = []
    if base_path_parts_for_relative is not None:
        current_path_parts.extend(base_path_parts_for_relative)

    # TODO to meny if (fix it)

    # 1. try to find <path>/<modul>.py
    # example.service.account_creator -> example/service/account_creator.py
    potential_file_path = "/".join(current_path_parts + module_path_parts) + ".py"
    potential_file_path = normalize_path(potential_file_path)
    if potential_file_path in project_files_normalized:
        return potential_file_path

    # 2.try to find <path>/<modul>/__init__.py
    # example.service.account_creator -> example/service/account_creator/__init__.py
    potential_package_path = (
        "/".join(current_path_parts + module_path_parts) + "/__init__.py"
    )
    potential_package_path = normalize_path(potential_package_path)
    if potential_package_path in project_files_normalized:
        return potential_package_path

    # 3. add root
    potential_file_path = (
        "/".join([project_root, *current_path_parts, *module_path_parts]) + ".py"
    )
    potential_file_path = normalize_path(potential_file_path)
    if potential_file_path in project_files_normalized:
        return potential_file_path

    # 4. add root
    potential_package_path = (
        "/".join([project_root, *current_path_parts, *module_path_parts])
        + "/__init__.py"
    )
    potential_package_path = normalize_path(potential_package_path)
    if potential_package_path in project_files_normalized:
        return potential_package_path

    return None


class NodeInfo(NamedTuple):
    id: str | None
    type: str


def resolve_import_string(
    import_str: str,
    source_file_path_normalized: str,
    project_root: str,
    project_files_normalized: set[str],
) -> NodeInfo:
    node_id: str | None = None
    node_type: str = "unresolved"

    source_parts = source_file_path_normalized.split("/")
    source_dir_parts = source_parts[:-1]

    # 1. relative import
    if import_str.startswith("."):
        num_dots = 0
        temp_module_part = import_str
        while temp_module_part.startswith("."):
            num_dots += 1
            temp_module_part = temp_module_part[1:]

        base_path_parts_relative: list[str]
        if num_dots == 1:  # from .module import ...
            base_path_parts_relative = source_dir_parts
        elif num_dots > 1:  # from ..module import ...
            levels_to_go_up = num_dots - 1
            if len(source_dir_parts) >= levels_to_go_up:
                base_path_parts_relative = source_dir_parts[:-levels_to_go_up]
            else:
                return NodeInfo(
                    import_str,
                    "unresolved_relative_too_many_dots",
                )
        else:
            return NodeInfo(import_str, "unresolved_relative_internal_error")

        module_candidate_parts = temp_module_part.split(".")

        for i in range(len(module_candidate_parts), 0, -1):
            current_module_try_parts = module_candidate_parts[:i]
            resolved_path = try_resolve_module_path(
                module_path_parts=current_module_try_parts,
                project_root=project_root,
                project_files_normalized=project_files_normalized,
                base_path_parts_for_relative=base_path_parts_relative,
            )
            if resolved_path:
                node_id = resolved_path
                node_type = "project_file"
                return NodeInfo(node_id, node_type)

        if not temp_module_part:  # from . import * (or ..)
            potential_package_path = "/".join(base_path_parts_relative) + "/__init__.py"
            if potential_package_path in project_files_normalized:
                return potential_package_path, "project_file"

        return NodeInfo(import_str, "unresolved_relative")

    # 2. absolute import
    absolute_module_parts = import_str.split(".")
    # if import_str == "example.repo.account_repo.AccountRepository":
    #     import pdb
    #
    #     pdb.set_trace()
    for i in range(len(absolute_module_parts), 0, -1):
        current_module_candidate_parts = absolute_module_parts[:i]
        resolved_path = try_resolve_module_path(
            module_path_parts=current_module_candidate_parts,
            project_root=project_root,
            project_files_normalized=project_files_normalized,
        )
        if resolved_path:
            node_id = resolved_path
            node_type = "project_file"
            return NodeInfo(node_id, node_type)

    root_module_name = absolute_module_parts[0]
    if root_module_name in STANDARD_LIB_MODULES:
        node_id = root_module_name
        node_type = "std_lib"
        return NodeInfo(node_id, node_type)

    node_id = root_module_name

    node_type = "external_lib"
    return NodeInfo(node_id, node_type)
