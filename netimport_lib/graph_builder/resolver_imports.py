"""Compatibility wrapper for import-resolution helpers."""

from netimport_lib.graph_builder.resolver import imports as _resolver_imports


normalize_path = _resolver_imports.normalize_path
resolve_import_string = _resolver_imports.resolve_import_string
