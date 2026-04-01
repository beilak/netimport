"""Configuration loading for NetImport."""

from collections.abc import Mapping
from pathlib import Path
from typing import Final, Literal, TypedDict

import toml


class NetImportConfigMap(TypedDict):
    """Validated NetImport configuration."""

    ignored_nodes: set[str]
    ignored_dirs: set[str]
    ignored_files: set[str]
    ignore_stdlib: bool
    ignore_external_lib: bool
    fail_on_unresolved_imports: bool
    forbidden_external_libs: set[str]


class PartialNetImportConfigMap(TypedDict, total=False):
    """Partial override for the NetImport configuration."""

    ignored_nodes: set[str]
    ignored_dirs: set[str]
    ignored_files: set[str]
    ignore_stdlib: bool
    ignore_external_lib: bool
    fail_on_unresolved_imports: bool
    forbidden_external_libs: set[str]


CONFIG_FILE_NAME: Final[str] = ".netimport.toml"
PYPROJECT_TOML_FILE: Final[str] = "pyproject.toml"
TOOL_SECTION_NAME: Final[str] = "tool"
APP_CONFIG_SECTION_NAME: Final[str] = "netimport"

StringSetConfigKey = Literal[
    "ignored_nodes",
    "ignored_dirs",
    "ignored_files",
    "forbidden_external_libs",
]
BoolConfigKey = Literal[
    "ignore_stdlib",
    "ignore_external_lib",
    "fail_on_unresolved_imports",
]
IGNORED_NODES_KEY: Final[StringSetConfigKey] = "ignored_nodes"
IGNORED_DIRS_KEY: Final[StringSetConfigKey] = "ignored_dirs"
IGNORED_FILES_KEY: Final[StringSetConfigKey] = "ignored_files"
IGNORE_STDLIB_KEY: Final[BoolConfigKey] = "ignore_stdlib"
IGNORE_EXTERNAL_LIB_KEY: Final[BoolConfigKey] = "ignore_external_lib"
FAIL_ON_UNRESOLVED_IMPORTS_KEY: Final[BoolConfigKey] = "fail_on_unresolved_imports"
FORBIDDEN_EXTERNAL_LIBS_KEY: Final[StringSetConfigKey] = "forbidden_external_libs"
STRING_SET_CONFIG_KEYS: Final[tuple[StringSetConfigKey, ...]] = (
    IGNORED_NODES_KEY,
    IGNORED_DIRS_KEY,
    IGNORED_FILES_KEY,
    FORBIDDEN_EXTERNAL_LIBS_KEY,
)
BOOL_CONFIG_KEYS: Final[tuple[BoolConfigKey, ...]] = (
    IGNORE_STDLIB_KEY,
    IGNORE_EXTERNAL_LIB_KEY,
    FAIL_ON_UNRESOLVED_IMPORTS_KEY,
)
KNOWN_CONFIG_KEYS: Final[frozenset[str]] = frozenset(
    (
        IGNORED_NODES_KEY,
        IGNORED_DIRS_KEY,
        IGNORED_FILES_KEY,
        IGNORE_STDLIB_KEY,
        IGNORE_EXTERNAL_LIB_KEY,
        FAIL_ON_UNRESOLVED_IMPORTS_KEY,
        FORBIDDEN_EXTERNAL_LIBS_KEY,
    )
)


class _ConfigTools:
    """Private namespace for config parsing helpers."""

    @classmethod
    def parse_string_set(
        cls,
        app_config: Mapping[str, object],
        key: StringSetConfigKey,
    ) -> set[str]:
        raw_value = app_config[key]
        if not isinstance(raw_value, list):
            raise TypeError(f"Config key '{key}' must be a list of strings.")
        if not all(isinstance(string_value, str) for string_value in raw_value):
            raise TypeError(f"Config key '{key}' must be a list of strings.")
        return set(raw_value)

    @classmethod
    def parse_bool(
        cls,
        app_config: Mapping[str, object],
        key: BoolConfigKey,
    ) -> bool:
        raw_value = app_config[key]
        if not isinstance(raw_value, bool):
            raise TypeError(f"Config key '{key}' must be a boolean.")
        return raw_value

    @classmethod
    def validate_config_keys(cls, app_config: Mapping[str, object]) -> None:
        unexpected_keys = sorted(set(app_config) - KNOWN_CONFIG_KEYS)
        if unexpected_keys:
            joined_keys = ", ".join(unexpected_keys)
            raise ValueError(f"Unknown NetImport config keys: {joined_keys}.")

    @classmethod
    def parse_config_object(
        cls,
        app_config: Mapping[str, object],
    ) -> PartialNetImportConfigMap:
        cls.validate_config_keys(app_config)
        parsed_config: PartialNetImportConfigMap = {}

        for string_key in STRING_SET_CONFIG_KEYS:
            if string_key in app_config:
                parsed_config[string_key] = cls.parse_string_set(app_config, string_key)
        for bool_key in BOOL_CONFIG_KEYS:
            if bool_key in app_config:
                parsed_config[bool_key] = cls.parse_bool(app_config, bool_key)
        return parsed_config

    @classmethod
    def load_toml_table(cls, config_path: Path) -> Mapping[str, object]:
        with config_path.open(encoding="utf-8") as file_handle:
            toml_data = toml.load(file_handle)
        if not isinstance(toml_data, Mapping):
            raise TypeError(f"Config file '{config_path}' must contain a TOML table.")
        return toml_data

    @classmethod
    def get_pyproject_app_config(
        cls,
        config_data: Mapping[str, object],
    ) -> Mapping[str, object] | None:
        tool_section = config_data.get(TOOL_SECTION_NAME)
        if not isinstance(tool_section, Mapping):
            return None

        app_config = tool_section.get(APP_CONFIG_SECTION_NAME)
        if not isinstance(app_config, Mapping):
            return None
        return app_config

    @classmethod
    def contains_known_config_keys(cls, config_data: Mapping[str, object]) -> bool:
        return any(key in config_data for key in KNOWN_CONFIG_KEYS)


def default_config() -> NetImportConfigMap:
    """Return the default NetImport configuration."""
    return NetImportConfigMap(
        ignored_nodes=set(),
        ignored_dirs=set(),
        ignored_files=set(),
        ignore_stdlib=False,
        ignore_external_lib=False,
        fail_on_unresolved_imports=False,
        forbidden_external_libs=set(),
    )


def merge_config(
    base_config: NetImportConfigMap,
    override_config: PartialNetImportConfigMap,
) -> NetImportConfigMap:
    """Return a full config with a partial override applied on top."""
    override_ignore_stdlib = override_config.get(IGNORE_STDLIB_KEY)
    override_ignore_external_lib = override_config.get(IGNORE_EXTERNAL_LIB_KEY)
    override_fail_on_unresolved_imports = override_config.get(FAIL_ON_UNRESOLVED_IMPORTS_KEY)

    return NetImportConfigMap(
        ignored_nodes=set(override_config.get(IGNORED_NODES_KEY, base_config[IGNORED_NODES_KEY])),
        ignored_dirs=set(override_config.get(IGNORED_DIRS_KEY, base_config[IGNORED_DIRS_KEY])),
        ignored_files=set(override_config.get(IGNORED_FILES_KEY, base_config[IGNORED_FILES_KEY])),
        ignore_stdlib=(
            base_config[IGNORE_STDLIB_KEY]
            if override_ignore_stdlib is None
            else override_ignore_stdlib
        ),
        ignore_external_lib=(
            base_config[IGNORE_EXTERNAL_LIB_KEY]
            if override_ignore_external_lib is None
            else override_ignore_external_lib
        ),
        fail_on_unresolved_imports=(
            base_config[FAIL_ON_UNRESOLVED_IMPORTS_KEY]
            if override_fail_on_unresolved_imports is None
            else override_fail_on_unresolved_imports
        ),
        forbidden_external_libs=set(
            override_config.get(
                FORBIDDEN_EXTERNAL_LIBS_KEY,
                base_config[FORBIDDEN_EXTERNAL_LIBS_KEY],
            )
        ),
    )


def load_explicit_config(config_path: str | Path) -> PartialNetImportConfigMap:
    """Load a NetImport override config from an explicit TOML file path."""
    resolved_config_path: Final[Path] = Path(config_path).resolve()
    config_data = _ConfigTools.load_toml_table(resolved_config_path)

    app_config = _ConfigTools.get_pyproject_app_config(config_data)
    if app_config is not None:
        return _ConfigTools.parse_config_object(app_config)
    if _ConfigTools.contains_known_config_keys(config_data):
        return _ConfigTools.parse_config_object(config_data)

    raise ValueError(
        f"Config file '{resolved_config_path}' does not contain NetImport config. "
        "Expected [tool.netimport] or top-level NetImport keys."
    )


def load_config(project_root: str) -> NetImportConfigMap:
    """Load the merged NetImport configuration for a project root."""
    project_root_path: Final[Path] = Path(project_root).resolve()
    pyproject_path = project_root_path / PYPROJECT_TOML_FILE
    merged_config = default_config()
    pyproject_app_config = (
        _ConfigTools.get_pyproject_app_config(_ConfigTools.load_toml_table(pyproject_path))
        if pyproject_path.exists()
        else None
    )
    if pyproject_app_config is not None:
        merged_config = merge_config(
            merged_config,
            _ConfigTools.parse_config_object(pyproject_app_config),
        )

    dot_netimport_path = project_root_path / CONFIG_FILE_NAME
    if dot_netimport_path.exists():
        merged_config = merge_config(
            merged_config,
            _ConfigTools.parse_config_object(_ConfigTools.load_toml_table(dot_netimport_path)),
        )
    return merged_config
