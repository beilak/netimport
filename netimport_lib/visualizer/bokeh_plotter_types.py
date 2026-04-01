"""Shared type aliases for the Bokeh visualizer."""

from collections.abc import Mapping
from typing import TypeAlias

from netimport_lib.visualizer.bokeh_plotter_contracts import NodeVisualData


FolderToNodesMap: TypeAlias = dict[str, list[str]]
FolderNames: TypeAlias = list[str]
LayoutPositionMap: TypeAlias = dict[str, tuple[float, float]]
NodeVisualDataMap: TypeAlias = Mapping[object, NodeVisualData]
MutableNodeVisualDataMap: TypeAlias = dict[object, NodeVisualData]
CollectedFolderNodes: TypeAlias = tuple[FolderToNodesMap, FolderNames]
FolderHierarchy: TypeAlias = tuple[FolderNames, FolderToNodesMap]
