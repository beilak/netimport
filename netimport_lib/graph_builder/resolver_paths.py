"""Compatibility wrapper for filesystem path resolution helpers."""

from netimport_lib.graph_builder.resolver import paths as _resolver_paths


normalize_path = _resolver_paths.normalize_path
resolve_longest_project_prefix = _resolver_paths.resolve_longest_project_prefix
