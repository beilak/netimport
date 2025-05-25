import os
import toml


CONFIG_FILE_NAME = ".netimport.toml"
PYPROJECT_TOML_FILE = "pyproject.toml"
TOOL_SECTION_NAME = "tool"
APP_CONFIG_SECTION_NAME = "netimport"


def parse_config_object(app_config) -> dict[str, set[str]]:
    ignored_dirs_list = app_config.get("ignored_dirs", [])
    ignored_files_list = app_config.get("ignored_files", [])

    if not isinstance(ignored_dirs_list, list) or not all(
        isinstance(item, str) for item in ignored_dirs_list
    ):
        ignored_dirs_list = []

    if not isinstance(ignored_files_list, list) or not all(
        isinstance(item, str) for item in ignored_files_list
    ):
        ignored_files_list = []

    config_data = {
        "ignored_dirs": set(ignored_dirs_list),
        "ignored_files": set(ignored_files_list),
    }
    # config_source_path = pyproject_path
    return config_data  # , config_source_path


def load_config(
    project_root: str,
) -> tuple[dict[str, set[str]] | None, str | None]:
    config_data: dict[str, set[str]] | None = None
    config_source_path: str | None = None

    # 1. .netimport.toml
    custom_config_path = os.path.join(project_root, CONFIG_FILE_NAME)
    if os.path.exists(custom_config_path):
        with open(custom_config_path, "r", encoding="utf-8") as f:
            data = toml.load(f)

        app_config: dict | None = None
        if APP_CONFIG_SECTION_NAME in data and isinstance(
            data[APP_CONFIG_SECTION_NAME], dict
        ):
            app_config = data[APP_CONFIG_SECTION_NAME]
        elif APP_CONFIG_SECTION_NAME not in data and (
            "ignored_dirs" in data or "ignored_files" in data
        ):
            app_config = data

        if app_config is not None:
            return parse_config_object(app_config), custom_config_path

    # 2. pyproject.toml
    pyproject_path = os.path.join(project_root, PYPROJECT_TOML_FILE)

    if os.path.exists(pyproject_path):
        with open(pyproject_path, "r", encoding="utf-8") as f:
            data = toml.load(f)

        if (
            TOOL_SECTION_NAME in data
            and isinstance(data[TOOL_SECTION_NAME], dict)
            and APP_CONFIG_SECTION_NAME in data[TOOL_SECTION_NAME]
            and isinstance(data[TOOL_SECTION_NAME][APP_CONFIG_SECTION_NAME], dict)
        ):
            app_config = data[TOOL_SECTION_NAME][APP_CONFIG_SECTION_NAME]
            return parse_config_object(app_config), pyproject_path

    return None, None
