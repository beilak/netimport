"""Compatibility wrapper for shared import-resolution types."""

from netimport_lib.graph_builder.resolver import shared as _resolver_shared


STANDARD_LIB_MODULES = _resolver_shared.STANDARD_LIB_MODULES
NodeInfo = _resolver_shared.NodeInfo
NodeType = _resolver_shared.NodeType
NodeTypes = _resolver_shared.NodeTypes
