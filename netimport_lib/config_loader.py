import os
from typing import TypedDict

import toml


class NetImportConfigMap(TypedDict):
    ignored_nodes: set[str]
    ignored_dirs: set[str]
    ignored_files: set[str]
    ignore_stdlib: bool
    ignore_external_lib: bool


CONFIG_FILE_NAME = ".netimport.toml"
PYPROJECT_TOML_FILE = "pyproject.toml"
TOOL_SECTION_NAME = "tool"
APP_CONFIG_SECTION_NAME = "netimport"


def parse_config_object(app_config) -> NetImportConfigMap:
    return NetImportConfigMap(
        ignored_nodes=set(app_config.get("ignored_nodes", [])),
        ignored_dirs=set(app_config.get("ignored_dirs", [])),
        ignored_files=set(app_config.get("ignored_files", [])),
        ignore_stdlib=app_config.get("ignore_stdlib", False),
        ignore_external_lib=app_config.get("ignore_external_lib", False),
    )
    # config_source_path = pyproject_path


def load_config(
    project_root: str,
) -> NetImportConfigMap:
    # config_data: dict[str, set[str]] | None = None
    # config_source_path: str | None = None

    # # 1. .netimport.toml # TODO
    # custom_config_path = os.path.join(project_root, CONFIG_FILE_NAME)
    # if os.path.exists(custom_config_path):
    #     with open(custom_config_path, "r", encoding="utf-8") as f:
    #         data = toml.load(f)
    #
    #     app_config: dict | None = None
    #     if APP_CONFIG_SECTION_NAME in data and isinstance(
    #         data[APP_CONFIG_SECTION_NAME], dict
    #     ):
    #         app_config = data[APP_CONFIG_SECTION_NAME]
    #     elif APP_CONFIG_SECTION_NAME not in data and (
    #         "ignored_dirs" in data or "ignored_files" in data
    #     ):
    #         app_config = data
    #
    #     if app_config is not None:
    #         return parse_config_object(app_config)

    # 2. pyproject.toml
    pyproject_path = os.path.join(project_root, PYPROJECT_TOML_FILE)

    if os.path.exists(pyproject_path):
        with open(pyproject_path, encoding="utf-8") as f:
            data = toml.load(f)

        if (
            TOOL_SECTION_NAME in data
            and isinstance(data[TOOL_SECTION_NAME], dict)
            and APP_CONFIG_SECTION_NAME in data[TOOL_SECTION_NAME]
            and isinstance(data[TOOL_SECTION_NAME][APP_CONFIG_SECTION_NAME], dict)
        ):
            app_config = data[TOOL_SECTION_NAME][APP_CONFIG_SECTION_NAME]
            return parse_config_object(app_config)

    return NetImportConfigMap(
        ignored_modes=set(),
        ignored_dirs=set(),
        ignored_files=set(),
        ignore_stdlib=False,
        ignore_external_lib=False,
    )
