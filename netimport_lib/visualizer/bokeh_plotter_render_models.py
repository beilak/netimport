"""Rendering and layout helper models for the Bokeh visualizer."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import networkx as nx

from netimport_lib.visualizer.bokeh_plotter_contracts import FolderRectData, NodeVisualData
from netimport_lib.visualizer.bokeh_plotter_layout_models import (
    ContainerLayout,
    LayoutTuning,
)


@dataclass(frozen=True, slots=True)
class EdgeVisualStyle:
    """Adaptive styling for edge and arrow rendering."""

    line_alpha: float
    line_width: float
    arrow_alpha: float
    arrow_line_width: float
    arrow_head_size: int


@dataclass(frozen=True, slots=True)
class RenderPolicy:
    """Adaptive renderer behavior for correctness and interactivity."""

    output_backend: Literal["canvas", "svg", "webgl"]
    show_arrows: bool
    lod_threshold: int | None
    lod_factor: int
    lod_interval: int
    lod_timeout: int


@dataclass(frozen=True, slots=True)
class FolderLayoutBuildContext:
    """Dependencies required to build nested folder container layouts."""

    graph: nx.DiGraph
    folder_to_nodes: Mapping[str, Sequence[str]]
    child_folders: Mapping[str, Sequence[str]]
    node_layout_k: float
    layout_tuning: LayoutTuning
    node_visual_data: Mapping[object, NodeVisualData]


@dataclass(slots=True)
class FolderPositionAssignment:
    """Mutable state used while assigning absolute folder positions."""

    folder_layouts: Mapping[str, ContainerLayout]
    folder_rect_data: FolderRectData
    final_positions: dict[str, tuple[float, float]]
    layout_tuning: LayoutTuning


@dataclass(frozen=True, slots=True)
class BlockScaleSpec:
    """Scaled layout block geometry."""

    width: float
    height: float
    inset: float


@dataclass(frozen=True, slots=True)
class LocalNodeLayoutSizing:
    """Geometry budget for a local spring layout block."""

    width: float
    height: float
    inset: float
    layout_k_multiplier: float


@dataclass(frozen=True, slots=True)
class PaddedLayoutSize:
    """Layout span after initial viewport padding."""

    width: float
    height: float
