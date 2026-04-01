"""Compatibility wrapper for configuration loading helpers."""

from netimport_lib.config import loader as _loader


APP_CONFIG_SECTION_NAME = _loader.APP_CONFIG_SECTION_NAME
BOOL_CONFIG_KEYS = _loader.BOOL_CONFIG_KEYS
CONFIG_FILE_NAME = _loader.CONFIG_FILE_NAME
FAIL_ON_UNRESOLVED_IMPORTS_KEY = _loader.FAIL_ON_UNRESOLVED_IMPORTS_KEY
FORBIDDEN_EXTERNAL_LIBS_KEY = _loader.FORBIDDEN_EXTERNAL_LIBS_KEY
IGNORE_EXTERNAL_LIB_KEY = _loader.IGNORE_EXTERNAL_LIB_KEY
IGNORE_STDLIB_KEY = _loader.IGNORE_STDLIB_KEY
IGNORED_DIRS_KEY = _loader.IGNORED_DIRS_KEY
IGNORED_FILES_KEY = _loader.IGNORED_FILES_KEY
IGNORED_NODES_KEY = _loader.IGNORED_NODES_KEY
KNOWN_CONFIG_KEYS = _loader.KNOWN_CONFIG_KEYS
PYPROJECT_TOML_FILE = _loader.PYPROJECT_TOML_FILE
STRING_SET_CONFIG_KEYS = _loader.STRING_SET_CONFIG_KEYS
TOOL_SECTION_NAME = _loader.TOOL_SECTION_NAME
BoolConfigKey = _loader.BoolConfigKey
NetImportConfigMap = _loader.NetImportConfigMap
PartialNetImportConfigMap = _loader.PartialNetImportConfigMap
StringSetConfigKey = _loader.StringSetConfigKey
default_config = _loader.default_config
load_config = _loader.load_config
load_explicit_config = _loader.load_explicit_config
merge_config = _loader.merge_config
