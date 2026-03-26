from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

import toml


class NetImportConfigMap(TypedDict):
    ignored_nodes: set[str]
    ignored_dirs: set[str]
    ignored_files: set[str]
    ignore_stdlib: bool
    ignore_external_lib: bool


class PartialNetImportConfigMap(TypedDict, total=False):
    ignored_nodes: set[str]
    ignored_dirs: set[str]
    ignored_files: set[str]
    ignore_stdlib: bool
    ignore_external_lib: bool


CONFIG_FILE_NAME = ".netimport.toml"
PYPROJECT_TOML_FILE = "pyproject.toml"
TOOL_SECTION_NAME = "tool"
APP_CONFIG_SECTION_NAME = "netimport"


def default_config() -> NetImportConfigMap:
    return NetImportConfigMap(
        ignored_nodes=set(),
        ignored_dirs=set(),
        ignored_files=set(),
        ignore_stdlib=False,
        ignore_external_lib=False,
    )


def _parse_string_set(app_config: Mapping[str, object], key: str) -> set[str]:
    value = app_config[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Config key '{key}' must be a list of strings.")

    return set(value)


def _parse_bool(app_config: Mapping[str, object], key: str) -> bool:
    value = app_config[key]
    if not isinstance(value, bool):
        raise ValueError(f"Config key '{key}' must be a boolean.")

    return value


def parse_config_object(app_config: Mapping[str, object]) -> PartialNetImportConfigMap:
    parsed_config: PartialNetImportConfigMap = {}

    if "ignored_nodes" in app_config:
        parsed_config["ignored_nodes"] = _parse_string_set(app_config, "ignored_nodes")
    if "ignored_dirs" in app_config:
        parsed_config["ignored_dirs"] = _parse_string_set(app_config, "ignored_dirs")
    if "ignored_files" in app_config:
        parsed_config["ignored_files"] = _parse_string_set(app_config, "ignored_files")
    if "ignore_stdlib" in app_config:
        parsed_config["ignore_stdlib"] = _parse_bool(app_config, "ignore_stdlib")
    if "ignore_external_lib" in app_config:
        parsed_config["ignore_external_lib"] = _parse_bool(app_config, "ignore_external_lib")

    return parsed_config


def _merge_config(
    base_config: NetImportConfigMap,
    override_config: PartialNetImportConfigMap,
) -> NetImportConfigMap:
    merged_config = default_config()
    merged_config.update(base_config)
    merged_config.update(override_config)
    return merged_config


def _load_pyproject_config(project_root: Path) -> PartialNetImportConfigMap:
    pyproject_path = project_root / PYPROJECT_TOML_FILE
    if not pyproject_path.exists():
        return {}

    with pyproject_path.open(encoding="utf-8") as file_handle:
        data = toml.load(file_handle)

    tool_section = data.get(TOOL_SECTION_NAME)
    if not isinstance(tool_section, dict):
        return {}

    app_config = tool_section.get(APP_CONFIG_SECTION_NAME)
    if not isinstance(app_config, dict):
        return {}

    return parse_config_object(app_config)


def _load_netimport_config(project_root: Path) -> PartialNetImportConfigMap:
    config_path = project_root / CONFIG_FILE_NAME
    if not config_path.exists():
        return {}

    with config_path.open(encoding="utf-8") as file_handle:
        data = toml.load(file_handle)

    if not isinstance(data, dict):
        raise ValueError(f"Config file '{config_path}' must contain a TOML table.")

    return parse_config_object(data)


def load_config(project_root: str) -> NetImportConfigMap:
    project_root_path = Path(project_root).resolve()

    loaded_config = default_config()
    loaded_config = _merge_config(loaded_config, _load_pyproject_config(project_root_path))
    loaded_config = _merge_config(loaded_config, _load_netimport_config(project_root_path))
    return loaded_config
