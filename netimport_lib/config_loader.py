"""Configuration loading for NetImport."""

from collections.abc import Mapping
from pathlib import Path
from typing import Final, TypedDict

import toml


class NetImportConfigMap(TypedDict):
    """Validated NetImport configuration."""

    ignored_nodes: set[str]
    ignored_dirs: set[str]
    ignored_files: set[str]
    ignore_stdlib: bool
    ignore_external_lib: bool


class PartialNetImportConfigMap(TypedDict, total=False):
    """Partial override for the NetImport configuration."""

    ignored_nodes: set[str]
    ignored_dirs: set[str]
    ignored_files: set[str]
    ignore_stdlib: bool
    ignore_external_lib: bool


CONFIG_FILE_NAME: Final[str] = ".netimport.toml"
PYPROJECT_TOML_FILE: Final[str] = "pyproject.toml"
TOOL_SECTION_NAME: Final[str] = "tool"
APP_CONFIG_SECTION_NAME: Final[str] = "netimport"

IGNORED_NODES_KEY: Final[str] = "ignored_nodes"
IGNORED_DIRS_KEY: Final[str] = "ignored_dirs"
IGNORED_FILES_KEY: Final[str] = "ignored_files"
IGNORE_STDLIB_KEY: Final[str] = "ignore_stdlib"
IGNORE_EXTERNAL_LIB_KEY: Final[str] = "ignore_external_lib"
KNOWN_CONFIG_KEYS: Final[frozenset[str]] = frozenset(
    {
        IGNORED_NODES_KEY,
        IGNORED_DIRS_KEY,
        IGNORED_FILES_KEY,
        IGNORE_STDLIB_KEY,
        IGNORE_EXTERNAL_LIB_KEY,
    }
)


def default_config() -> NetImportConfigMap:
    """Return the default NetImport configuration."""
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
        raise TypeError(f"Config key '{key}' must be a list of strings.")

    return set(value)


def _parse_bool(app_config: Mapping[str, object], key: str) -> bool:
    value = app_config[key]
    if not isinstance(value, bool):
        raise TypeError(f"Config key '{key}' must be a boolean.")

    return value


def _validate_config_keys(app_config: Mapping[str, object]) -> None:
    unexpected_keys = sorted(set(app_config) - KNOWN_CONFIG_KEYS)
    if unexpected_keys:
        joined_keys = ", ".join(unexpected_keys)
        raise ValueError(f"Unknown NetImport config keys: {joined_keys}.")


def _parse_config_object(app_config: Mapping[str, object]) -> PartialNetImportConfigMap:
    _validate_config_keys(app_config)

    parsed_config: PartialNetImportConfigMap = {}

    if "ignored_nodes" in app_config:
        parsed_config["ignored_nodes"] = _parse_string_set(app_config, IGNORED_NODES_KEY)
    if "ignored_dirs" in app_config:
        parsed_config["ignored_dirs"] = _parse_string_set(app_config, IGNORED_DIRS_KEY)
    if "ignored_files" in app_config:
        parsed_config["ignored_files"] = _parse_string_set(app_config, IGNORED_FILES_KEY)
    if "ignore_stdlib" in app_config:
        parsed_config["ignore_stdlib"] = _parse_bool(app_config, IGNORE_STDLIB_KEY)
    if "ignore_external_lib" in app_config:
        parsed_config["ignore_external_lib"] = _parse_bool(app_config, IGNORE_EXTERNAL_LIB_KEY)

    return parsed_config


def _merge_config(
    base_config: NetImportConfigMap,
    override_config: PartialNetImportConfigMap,
) -> NetImportConfigMap:
    ignored_nodes = set(base_config["ignored_nodes"])
    ignored_dirs = set(base_config["ignored_dirs"])
    ignored_files = set(base_config["ignored_files"])
    ignore_stdlib = base_config["ignore_stdlib"]
    ignore_external_lib = base_config["ignore_external_lib"]

    if "ignored_nodes" in override_config:
        ignored_nodes = set(override_config["ignored_nodes"])
    if "ignored_dirs" in override_config:
        ignored_dirs = set(override_config["ignored_dirs"])
    if "ignored_files" in override_config:
        ignored_files = set(override_config["ignored_files"])
    if "ignore_stdlib" in override_config:
        ignore_stdlib = override_config["ignore_stdlib"]
    if "ignore_external_lib" in override_config:
        ignore_external_lib = override_config["ignore_external_lib"]

    return NetImportConfigMap(
        ignored_nodes=ignored_nodes,
        ignored_dirs=ignored_dirs,
        ignored_files=ignored_files,
        ignore_stdlib=ignore_stdlib,
        ignore_external_lib=ignore_external_lib,
    )


def _load_pyproject_config(project_root: Path) -> PartialNetImportConfigMap:
    pyproject_path = project_root / PYPROJECT_TOML_FILE
    if not pyproject_path.exists():
        return {}

    with pyproject_path.open(encoding="utf-8") as file_handle:
        data = toml.load(file_handle)

    tool_section = data.get(TOOL_SECTION_NAME)
    if not isinstance(tool_section, Mapping):
        return {}

    app_config = tool_section.get(APP_CONFIG_SECTION_NAME)
    if not isinstance(app_config, Mapping):
        return {}

    return _parse_config_object(app_config)


def _load_netimport_config(project_root: Path) -> PartialNetImportConfigMap:
    config_path = project_root / CONFIG_FILE_NAME
    if not config_path.exists():
        return {}

    with config_path.open(encoding="utf-8") as file_handle:
        data = toml.load(file_handle)

    if not isinstance(data, Mapping):
        raise TypeError(f"Config file '{config_path}' must contain a TOML table.")

    return _parse_config_object(data)


def load_config(project_root: str) -> NetImportConfigMap:
    """Load the merged NetImport configuration for a project root."""
    project_root_path: Final[Path] = Path(project_root).resolve()
    pyproject_config = _load_pyproject_config(project_root_path)
    dot_netimport_config = _load_netimport_config(project_root_path)

    return _merge_config(
        _merge_config(default_config(), pyproject_config),
        dot_netimport_config,
    )
