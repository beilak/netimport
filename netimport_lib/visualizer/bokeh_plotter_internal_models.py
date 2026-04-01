"""Internal helper models for the Bokeh visualizer."""

from dataclasses import dataclass
from typing import Any, Protocol, cast

from bokeh import models as bokeh_models

from netimport_lib.visualizer.bokeh_plotter_layout_models import ContainerLayout
from netimport_lib.visualizer.bokeh_plotter_render_models import FolderLayoutBuildContext


@dataclass(frozen=True, slots=True)
class PackedBoxFrame:
    """Derived grid metrics used while packing child boxes."""

    column_count: int
    total_width: float
    total_height: float
    column_widths: list[float]
    row_heights: list[float]


@dataclass(frozen=True, slots=True)
class SectionPlacement:
    """Shared placement result for sibling layout sections."""

    total_width: float
    total_height: float
    primary_origin: tuple[float, float]
    secondary_origin: tuple[float, float]


@dataclass(frozen=True, slots=True)
class FolderLayoutSourceData:
    """Source metadata needed to build constrained folder layouts."""

    folder_to_nodes: dict[str, list[str]]
    root_folder_nodes: list[str]
    root_folders: list[str]
    child_folders: dict[str, list[str]]


@dataclass(frozen=True, slots=True)
class ConstrainedLayoutData:
    """Precomputed dependencies for constrained layout construction."""

    source_data: FolderLayoutSourceData
    build_context: FolderLayoutBuildContext
    folder_layouts: dict[str, ContainerLayout]


class BokehRendererLayer(Protocol):
    """Renderer layer attributes accessed while configuring Bokeh glyphs."""

    data_source: bokeh_models.ColumnDataSource
    glyph: object
    selection_glyph: object | None
    hover_glyph: object | None


class GraphRendererLike(Protocol):
    """Subset of GraphRenderer API used by the renderer helper."""

    @property
    def node_renderer(self) -> object:
        """Return the configured node renderer."""

    @property
    def edge_renderer(self) -> object:
        """Return the configured edge renderer."""


_BokehRendererLayer = BokehRendererLayer
_GraphRendererLike = GraphRendererLike
_BOKEH_MODELS_ANY = cast("Any", bokeh_models)
