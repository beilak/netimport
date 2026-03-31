"""Bokeh-based graph rendering."""

import math
import tempfile
import webbrowser
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal, Protocol, TypeAlias, TypedDict, cast, overload

import networkx as nx
from bokeh import io as bokeh_io
from bokeh import models as bokeh_models
from bokeh import plotting as bokeh_plotting
from bokeh import resources as bokeh_resources


class ArrowSourceData(TypedDict):
    """Arrow renderer coordinates."""

    start_x: list[float]
    start_y: list[float]
    end_x: list[float]
    end_y: list[float]


class NodeVisualData(TypedDict):
    """Visual attributes derived from graph metadata."""

    viz_size: int
    viz_color: str
    viz_label: str
    viz_degree: int
    viz_type: str
    viz_label_y_offset: int
    in_degree: int
    out_degree: int
    total_degree: int


FolderRectDataSource: TypeAlias = dict[str, list[float] | list[str]]


@dataclass(slots=True)
class FolderRectData:
    """Column-oriented folder rectangle data for Bokeh."""

    center_xs: list[float] = field(default_factory=list)
    center_ys: list[float] = field(default_factory=list)
    label_ys: list[float] = field(default_factory=list)
    widths: list[float] = field(default_factory=list)
    heights: list[float] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)

    @property
    def folder_count(self) -> int:
        """Return the total number of recorded folder rectangles."""
        return len(self.names)

    def append_folder(
        self,
        folder_name: str,
        origin_x: float,
        origin_y: float,
        layout: "ContainerLayout",
        layout_tuning: "LayoutTuning",
    ) -> None:
        """Append a folder rectangle and label placement."""
        self.center_xs.append(origin_x + _half(layout.width))
        self.center_ys.append(origin_y + _half(layout.height))
        self.label_ys.append(
            origin_y
            + layout.height
            - layout_tuning.folder_padding_y
            - _half(layout_tuning.folder_label_height)
        )
        self.widths.append(layout.width)
        self.heights.append(layout.height)
        self.names.append(folder_name.rsplit("/", maxsplit=1)[-1])
        self.colors.append(FOLDER_RECT_FILL_COLOR)

    @overload
    def __getitem__(
        self,
        field_name: Literal["x", "y", "label_y", "width", "height"],
    ) -> list[float]: ...

    @overload
    def __getitem__(self, field_name: Literal["name", "color"]) -> list[str]: ...

    def __getitem__(self, field_name: str) -> list[float] | list[str]:
        """Provide backwards-compatible dict-style access for tests and callers."""
        return self.as_column_data()[field_name]

    def __eq__(self, other: object) -> bool:
        """Keep comparisons compatible with the legacy dict payload shape."""
        if isinstance(other, FolderRectData):
            return self.as_column_data() == other.as_column_data()
        if isinstance(other, dict):
            return self.as_column_data() == other
        return False

    def __hash__(self) -> int:
        """Hash the column payload so the custom equality stays well-defined."""
        return hash(
            (
                tuple(self.center_xs),
                tuple(self.center_ys),
                tuple(self.label_ys),
                tuple(self.widths),
                tuple(self.heights),
                tuple(self.names),
                tuple(self.colors),
            ),
        )

    def as_column_data(self) -> FolderRectDataSource:
        """Return the Bokeh ``ColumnDataSource`` payload."""
        return {
            FOLDER_X_FIELD: self.center_xs,
            FOLDER_Y_FIELD: self.center_ys,
            FOLDER_LABEL_Y_FIELD: self.label_ys,
            FOLDER_WIDTH_FIELD: self.widths,
            FOLDER_HEIGHT_FIELD: self.heights,
            FOLDER_NAME_FIELD: self.names,
            FOLDER_COLOR_FIELD: self.colors,
        }


@dataclass(frozen=True, slots=True)
class PreparedBokehRender:
    """Data prepared for Bokeh rendering."""

    final_positions: "LayoutPositionMap"
    folder_rect_data: FolderRectData
    arrow_source_data: ArrowSourceData
    node_visual_data: "MutableNodeVisualDataMap"


@dataclass(frozen=True, slots=True)
class LocalNodeLayout:
    """Relative node placement within a container block."""

    width: float
    height: float
    positions: dict[str, tuple[float, float]]


@dataclass(frozen=True, slots=True)
class PackedBoxLayout:
    """Packed child-box placement within a container block."""

    width: float
    height: float
    origins: dict[str, tuple[float, float]]


@dataclass(frozen=True, slots=True)
class ContainerLayout:
    """Computed box geometry for a folder or synthetic root container."""

    width: float
    height: float
    node_positions: "LayoutPositionMap"
    child_origins: "LayoutPositionMap"


@dataclass(frozen=True, slots=True)
class LayoutTuning:
    """Adaptive spacing values for constrained layout."""

    min_node_block_span: float
    node_block_cell_span: float
    node_layout_inset: float
    folder_padding_x: float
    folder_padding_y: float
    folder_label_height: float
    folder_section_gap: float
    folder_grid_gap_x: float
    folder_grid_gap_y: float
    root_section_gap: float
    min_folder_content_width: float
    min_folder_content_height: float


@dataclass(frozen=True, slots=True)
class PlotDimensions:
    """Pixel dimensions for the rendered Bokeh plot."""

    width: int
    height: int


@dataclass(frozen=True, slots=True)
class LayoutBounds:
    """Measured layout extents in data coordinates."""

    min_x: float
    max_x: float
    min_y: float
    max_y: float

    @property
    def width(self) -> float:
        """Return the horizontal span of the measured bounds."""
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        """Return the vertical span of the measured bounds."""
        return self.max_y - self.min_y


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


FREEZE_RANDOM_SEED: Final[int] = 42
LABEL_PADDING: Final[float] = 20.0
MIN_NODE_SIZE: Final[int] = 20
MEDIUM_GRAPH_MIN_NODE_SIZE: Final[int] = 18
COMPACT_GRAPH_MIN_NODE_SIZE: Final[int] = 16
MAX_NODE_SIZE: Final[int] = 60
MEDIUM_GRAPH_MAX_NODE_SIZE: Final[int] = 50
COMPACT_GRAPH_MAX_NODE_SIZE: Final[int] = 42
NODE_SIZE_SQRT_SCALE: Final[float] = 6.0
MEDIUM_GRAPH_NODE_SIZE_SQRT_SCALE: Final[float] = 5.0
COMPACT_GRAPH_NODE_SIZE_SQRT_SCALE: Final[float] = 4.0
MEDIUM_GRAPH_NODE_COUNT_THRESHOLD: Final[int] = 80
COMPACT_GRAPH_NODE_COUNT_THRESHOLD: Final[int] = 180
MEDIUM_EDGE_COUNT_THRESHOLD: Final[int] = 140
COMPACT_EDGE_COUNT_THRESHOLD: Final[int] = 320
ARROW_RENDER_NODE_THRESHOLD: Final[int] = 90
ARROW_RENDER_EDGE_THRESHOLD: Final[int] = 140
LOD_RENDER_NODE_THRESHOLD: Final[int] = 120
LOD_RENDER_EDGE_THRESHOLD: Final[int] = 180
LOD_FACTOR: Final[int] = 6
LOD_INTERVAL_MS: Final[int] = 120
LOD_TIMEOUT_MS: Final[int] = 80
INITIAL_VIEW_PADDING_FRACTION: Final[float] = 0.14
INITIAL_VIEW_MIN_PADDING_UNITS: Final[float] = 4.0
INITIAL_VIEW_SAFETY_SCALE: Final[float] = 1.06
MIN_NODE_BLOCK_SPAN: Final[float] = 4.0
NODE_BLOCK_CELL_SPAN: Final[float] = 4.0
NODE_LAYOUT_INSET: Final[float] = 0.75
NODE_LAYOUT_CLEARANCE_UNITS: Final[float] = 1.4
NODE_LAYOUT_OUTER_PADDING_UNITS: Final[float] = 0.8
LAYOUT_VIEWPORT_PADDING_UNITS: Final[float] = 2.5
FOLDER_PADDING_X: Final[float] = 1.5
FOLDER_PADDING_Y: Final[float] = 1.5
FOLDER_LABEL_HEIGHT: Final[float] = 1.75
FOLDER_SECTION_GAP: Final[float] = 1.5
FOLDER_GRID_GAP_X: Final[float] = 2.0
FOLDER_GRID_GAP_Y: Final[float] = 2.0
ROOT_SECTION_GAP: Final[float] = 3.0
MIN_FOLDER_CONTENT_WIDTH: Final[float] = 4.0
MIN_FOLDER_CONTENT_HEIGHT: Final[float] = 3.0
DEFAULT_NODE_LAYOUT_K: Final[float] = 0.5
BASE_PLOT_WIDTH: Final[int] = 1040
BASE_PLOT_HEIGHT: Final[int] = 780
MAX_PLOT_WIDTH: Final[int] = 1800
MAX_PLOT_HEIGHT: Final[int] = 1320
PLOT_PIXELS_PER_LAYOUT_UNIT: Final[float] = 30.0
TOOLBAR_BUTTON_WIDTH_PX: Final[int] = 38
TOOLBAR_BUTTON_HEIGHT_PX: Final[int] = 38
TOOLBAR_ICON_SCALE_PERCENT: Final[int] = 72
TOOLBAR_VIEWPORT_LEFT_PX: Final[int] = 16
TOOLBAR_VIEWPORT_TOP_PX: Final[int] = 16
DEFAULT_NODE_COLOR: Final[str] = "red"
BOKEH_OUTPUT_PREFIX: Final[str] = "netimport-"
BOKEH_OUTPUT_SUFFIX: Final[str] = ".html"
BOKEH_PLOT_TITLE: Final[str] = "NetImport dependency graph"
INTERACTIVE_PLOT_TITLE: Final[str] = "Interactive dependency graph"
SKIPPED_AUTO_OPEN_CONTROLLER_NAMES: Final[frozenset[str]] = frozenset(("MacOSXOSAScript",))
ZERO_FLOAT: Final = 0
HALF_DIVISOR: Final[float] = 2.0
SPRING_LAYOUT_ITERATIONS: Final[int] = 50
LAYOUT_DENSITY_DIVISOR: Final[float] = 6.0
LAYOUT_FOLDER_SCALE_LIMIT: Final[float] = 0.6
LAYOUT_FOLDER_DIVISOR: Final[float] = 7.0
LAYOUT_GAP_SCALE_FACTOR: Final[float] = 1.35
LAYOUT_PADDING_SCALE_FACTOR: Final[float] = 0.7
LAYOUT_INSET_SCALE_FACTOR: Final[float] = 0.3
SIDE_BY_SIDE_AREA_THRESHOLD: Final[float] = 6.0
EMPTY_PLOT_RANGE_EXTENT: Final[float] = 2.0
MIN_PLOT_ASPECT_RATIO: Final[float] = 1e-6
FOLDER_RECT_FILL_COLOR: Final[str] = "#E8E8E8"
BLACK_COLOR: Final[str] = "black"
FOLDER_RECT_FILL_ALPHA: Final[float] = 0.4
NODE_FILL_ALPHA: Final[float] = 0.8
EDGE_HOVER_LINE_ALPHA: Final[float] = 0.9
EDGE_SELECTION_LINE_ALPHA: Final[float] = 0.95
COMPACT_EDGE_LINE_ALPHA: Final[float] = 0.12
COMPACT_EDGE_LINE_WIDTH: Final[float] = 0.9
COMPACT_ARROW_ALPHA: Final[float] = 0.18
MEDIUM_EDGE_LINE_ALPHA: Final[float] = 0.18
MEDIUM_ARROW_ALPHA: Final[float] = 0.24
MEDIUM_ARROW_LINE_WIDTH: Final[float] = 1.2
DEFAULT_EDGE_LINE_ALPHA: Final[float] = 0.28
DEFAULT_EDGE_LINE_WIDTH: Final[float] = 1.2
DEFAULT_ARROW_ALPHA: Final[float] = 0.32
DEFAULT_ARROW_LINE_WIDTH: Final[float] = 1.4
FOLDER_X_FIELD: Final[str] = "x"
FOLDER_Y_FIELD: Final[str] = "y"
FOLDER_LABEL_Y_FIELD: Final[str] = "label_y"
FOLDER_WIDTH_FIELD: Final[str] = "width"
FOLDER_HEIGHT_FIELD: Final[str] = "height"
FOLDER_NAME_FIELD: Final[str] = "name"
FOLDER_COLOR_FIELD: Final[str] = "color"
VIZ_SIZE_FIELD: Final[str] = "viz_size"
LAYOUT_POSITION_PADDING_MULTIPLIER: Final[float] = 2.0
PLOT_NODE_COMPLEXITY_THRESHOLD: Final[int] = 12
PLOT_FOLDER_COMPLEXITY_THRESHOLD: Final[int] = 4
PLOT_WIDTH_NODE_STEP: Final[int] = 18
PLOT_WIDTH_FOLDER_STEP: Final[int] = 90
PLOT_HEIGHT_NODE_STEP: Final[int] = 14
PLOT_HEIGHT_FOLDER_STEP: Final[int] = 72
PLOT_WIDTH_NODE_SIZE_STEP: Final[int] = 6
PLOT_HEIGHT_NODE_SIZE_STEP: Final[int] = 5
FolderToNodesMap: TypeAlias = dict[str, list[str]]
FolderNames: TypeAlias = list[str]
LayoutPositionMap: TypeAlias = dict[str, tuple[float, float]]
NodeVisualDataMap: TypeAlias = Mapping[object, NodeVisualData]
MutableNodeVisualDataMap: TypeAlias = dict[object, NodeVisualData]
CollectedFolderNodes: TypeAlias = tuple[FolderToNodesMap, FolderNames]
FolderHierarchy: TypeAlias = tuple[FolderNames, FolderToNodesMap]


class _BokehRendererLayer(Protocol):
    data_source: bokeh_models.ColumnDataSource
    glyph: object
    selection_glyph: object | None
    hover_glyph: object | None


class _GraphRendererLike(Protocol):
    @property
    def node_renderer(self) -> object: ...

    @property
    def edge_renderer(self) -> object: ...


_BOKEH_MODELS_ANY = cast("Any", bokeh_models)


COMPACT_EDGE_STYLE: Final[EdgeVisualStyle] = EdgeVisualStyle(
    line_alpha=COMPACT_EDGE_LINE_ALPHA,
    line_width=COMPACT_EDGE_LINE_WIDTH,
    arrow_alpha=COMPACT_ARROW_ALPHA,
    arrow_line_width=1.0,
    arrow_head_size=8,
)
MEDIUM_EDGE_STYLE: Final[EdgeVisualStyle] = EdgeVisualStyle(
    line_alpha=MEDIUM_EDGE_LINE_ALPHA,
    line_width=1.0,
    arrow_alpha=MEDIUM_ARROW_ALPHA,
    arrow_line_width=MEDIUM_ARROW_LINE_WIDTH,
    arrow_head_size=9,
)
DEFAULT_EDGE_STYLE: Final[EdgeVisualStyle] = EdgeVisualStyle(
    line_alpha=DEFAULT_EDGE_LINE_ALPHA,
    line_width=DEFAULT_EDGE_LINE_WIDTH,
    arrow_alpha=DEFAULT_ARROW_ALPHA,
    arrow_line_width=DEFAULT_ARROW_LINE_WIDTH,
    arrow_head_size=10,
)


def _build_color_map() -> Mapping[str, str]:
    return {
        "project_file": "skyblue",
        "std_lib": "lightgreen",
        "external_lib": "salmon",
        "unresolved": "lightgray",
        "unresolved_relative": "silver",
        "unresolved_relative_internal_error": "silver",
        "unresolved_relative_too_many_dots": "silver",
    }


COLOR_MAP: Final[Mapping[str, str]] = _build_color_map()


@dataclass(frozen=True, slots=True)
class FolderLayoutBuildContext:
    """Dependencies required to build nested folder container layouts."""

    graph: nx.DiGraph
    folder_to_nodes: Mapping[str, Sequence[str]]
    child_folders: Mapping[str, Sequence[str]]
    node_layout_k: float
    layout_tuning: LayoutTuning
    node_visual_data: NodeVisualDataMap


@dataclass(slots=True)
class FolderPositionAssignment:
    """Mutable state used while assigning absolute folder positions."""

    folder_layouts: Mapping[str, ContainerLayout]
    folder_rect_data: FolderRectData
    final_positions: LayoutPositionMap
    layout_tuning: LayoutTuning


@dataclass(frozen=True, slots=True)
class BlockScaleSpec:
    """Scaled layout block geometry."""

    width: float
    height: float
    inset: float

    @property
    def center_x(self) -> float:
        """Return the horizontal center of the block."""
        return _half(self.width)

    @property
    def center_y(self) -> float:
        """Return the vertical center of the block."""
        return _half(self.height)

    @property
    def usable_width(self) -> float:
        """Return the horizontal span available for scaled positions."""
        return max(
            self.width - LAYOUT_POSITION_PADDING_MULTIPLIER * self.inset,
            ZERO_FLOAT,
        )

    @property
    def usable_height(self) -> float:
        """Return the vertical span available for scaled positions."""
        return max(
            self.height - LAYOUT_POSITION_PADDING_MULTIPLIER * self.inset,
            ZERO_FLOAT,
        )


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

    folder_to_nodes: FolderToNodesMap
    root_folder_nodes: FolderNames
    root_folders: FolderNames
    child_folders: FolderToNodesMap


@dataclass(frozen=True, slots=True)
class ConstrainedLayoutData:
    """Precomputed dependencies for constrained layout construction."""

    source_data: FolderLayoutSourceData
    build_context: FolderLayoutBuildContext
    folder_layouts: dict[str, ContainerLayout]


def _half(numeric_value: float) -> float:
    return numeric_value / HALF_DIVISOR


def _node_item_sort_key(node_item: tuple[object, object]) -> str:
    return str(node_item[0])


def _named_item_sort_key(named_item: tuple[str, float, float]) -> str:
    return named_item[0]


def _edge_sort_key(edge_item: tuple[object, object]) -> tuple[str, str]:
    return (str(edge_item[0]), str(edge_item[1]))


def _folder_depth_sort_key(folder_name: str) -> tuple[int, str]:
    return (folder_name.count("/"), folder_name)


def _parent_folder_name(folder_name: str) -> str:
    return "/".join(folder_name.split("/")[:-1])


def _normalize_layout_positions(
    raw_positions: Mapping[str, Sequence[float]],
) -> LayoutPositionMap:
    return {
        node_id: (float(position[0]), float(position[1]))
        for node_id, position in raw_positions.items()
    }


def _collect_folder_nodes(graph: nx.DiGraph) -> CollectedFolderNodes:
    folder_to_nodes: dict[str, list[str]] = {}
    root_folder_nodes: FolderNames = []

    for node_id, node_data in sorted(graph.nodes(data=True), key=_node_item_sort_key):
        folder_name = str(node_data.get("folder", ""))
        if bool(node_data.get("is_root_folder", False)):
            root_folder_nodes.append(str(node_id))
            continue

        folder_to_nodes.setdefault(folder_name, []).append(str(node_id))

    return dict(folder_to_nodes), root_folder_nodes


def _build_folder_hierarchy(
    folder_to_nodes: Mapping[str, Sequence[str]],
) -> FolderHierarchy:
    all_folders = tuple(sorted(folder_to_nodes))
    root_folders: list[str] = []
    child_folders: dict[str, list[str]] = {folder_name: [] for folder_name in all_folders}

    for folder_name in all_folders:
        siblings = child_folders.get(_parent_folder_name(folder_name))
        if siblings is not None:
            siblings.append(folder_name)
            continue
        root_folders.append(folder_name)

    for siblings in child_folders.values():
        siblings.sort()
    root_folders.sort()

    return root_folders, child_folders


def _build_sorted_layout_subgraph(
    graph: nx.DiGraph,
    node_ids: Sequence[str],
) -> nx.DiGraph:
    ordered_nodes = tuple(sorted(node_ids))
    subgraph = nx.DiGraph()
    for node_id in ordered_nodes:
        subgraph.add_node(node_id)
    for start_node, end_node in sorted(graph.subgraph(ordered_nodes).edges(), key=_edge_sort_key):
        subgraph.add_edge(start_node, end_node)
    return subgraph


def _clamp_float(numeric_value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(numeric_value, maximum))


def _resolve_node_size_budget(node_count: int) -> tuple[int, int, float]:
    if node_count >= COMPACT_GRAPH_NODE_COUNT_THRESHOLD:
        return (
            COMPACT_GRAPH_MIN_NODE_SIZE,
            COMPACT_GRAPH_MAX_NODE_SIZE,
            COMPACT_GRAPH_NODE_SIZE_SQRT_SCALE,
        )
    if node_count >= MEDIUM_GRAPH_NODE_COUNT_THRESHOLD:
        return (
            MEDIUM_GRAPH_MIN_NODE_SIZE,
            MEDIUM_GRAPH_MAX_NODE_SIZE,
            MEDIUM_GRAPH_NODE_SIZE_SQRT_SCALE,
        )
    return (MIN_NODE_SIZE, MAX_NODE_SIZE, NODE_SIZE_SQRT_SCALE)


def _calculate_node_visual_size(degree: int, node_count: int) -> int:
    minimum_size, maximum_size, sqrt_scale = _resolve_node_size_budget(node_count)
    calculated_size = minimum_size + math.sqrt(max(degree, 0)) * sqrt_scale
    return round(_clamp_float(calculated_size, float(minimum_size), float(maximum_size)))


def _get_node_visual_size(
    node_visual_data: NodeVisualDataMap,
    node_id: str,
) -> int:
    visual_data = node_visual_data.get(node_id)
    if visual_data is None:
        return MIN_NODE_SIZE
    return max(_to_int(visual_data.get(VIZ_SIZE_FIELD, MIN_NODE_SIZE)), 1)


def _node_visual_diameter_units(node_visual_size: int) -> float:
    return float(node_visual_size) / PLOT_PIXELS_PER_LAYOUT_UNIT


def _node_visual_radius_units(node_visual_size: int) -> float:
    return _half(_node_visual_diameter_units(node_visual_size))


def _build_layout_spacing_scale(node_count: int, folder_count: int) -> float:
    density_factor = math.log2(node_count + 1) / LAYOUT_DENSITY_DIVISOR
    density_scale = 1.0 + min(1.0, density_factor)
    folder_scale = 1.0 + min(
        LAYOUT_FOLDER_SCALE_LIMIT,
        math.log2(folder_count + 1) / LAYOUT_FOLDER_DIVISOR,
    )
    return max(density_scale, folder_scale)


def _build_layout_tuning(
    graph: nx.DiGraph,
    folder_to_nodes: Mapping[str, Sequence[str]],
) -> LayoutTuning:
    node_count = max(graph.number_of_nodes(), 1)
    folder_count = max(len(folder_to_nodes), 1)
    spacing_scale = _build_layout_spacing_scale(node_count, folder_count)
    gap_scale = 1.0 + (spacing_scale - 1.0) * LAYOUT_GAP_SCALE_FACTOR
    padding_scale = 1.0 + (spacing_scale - 1.0) * LAYOUT_PADDING_SCALE_FACTOR

    return LayoutTuning(
        min_node_block_span=MIN_NODE_BLOCK_SPAN * spacing_scale,
        node_block_cell_span=NODE_BLOCK_CELL_SPAN * spacing_scale,
        node_layout_inset=NODE_LAYOUT_INSET
        * (1.0 + (spacing_scale - 1.0) * LAYOUT_INSET_SCALE_FACTOR),
        folder_padding_x=FOLDER_PADDING_X * padding_scale,
        folder_padding_y=FOLDER_PADDING_Y * padding_scale,
        folder_label_height=FOLDER_LABEL_HEIGHT * padding_scale,
        folder_section_gap=FOLDER_SECTION_GAP * gap_scale,
        folder_grid_gap_x=FOLDER_GRID_GAP_X * gap_scale,
        folder_grid_gap_y=FOLDER_GRID_GAP_Y * gap_scale,
        root_section_gap=ROOT_SECTION_GAP * gap_scale,
        min_folder_content_width=MIN_FOLDER_CONTENT_WIDTH * padding_scale,
        min_folder_content_height=MIN_FOLDER_CONTENT_HEIGHT * padding_scale,
    )


def _measure_position_bounds(
    raw_positions: Mapping[str, tuple[float, float]],
) -> LayoutBounds:
    points = tuple(raw_positions.values())
    return LayoutBounds(
        min_x=min(x_coord for x_coord, _ in points),
        max_x=max(x_coord for x_coord, _ in points),
        min_y=min(y_coord for _, y_coord in points),
        max_y=max(y_coord for _, y_coord in points),
    )


def _scale_axis_value(
    raw_value: float,
    bounds: tuple[float, float],
    usable_extent: float,
    axis_center: float,
    inset: float,
) -> float:
    if bounds[1] == bounds[0]:
        return axis_center
    return inset + _scale_axis_ratio(raw_value, bounds) * usable_extent


def _scale_axis_ratio(raw_value: float, bounds: tuple[float, float]) -> float:
    return (raw_value - bounds[0]) / (bounds[1] - bounds[0])


def _scale_block_point(
    raw_point: tuple[float, float],
    position_bounds: LayoutBounds,
    scale_spec: BlockScaleSpec,
) -> tuple[float, float]:
    return (
        _scale_axis_value(
            raw_point[0],
            (position_bounds.min_x, position_bounds.max_x),
            scale_spec.usable_width,
            scale_spec.center_x,
            scale_spec.inset,
        ),
        _scale_axis_value(
            raw_point[1],
            (position_bounds.min_y, position_bounds.max_y),
            scale_spec.usable_height,
            scale_spec.center_y,
            scale_spec.inset,
        ),
    )


def _scale_positions_to_block(
    raw_positions: Mapping[str, tuple[float, float]],
    scale_spec: BlockScaleSpec,
) -> LayoutPositionMap:
    if not raw_positions:
        return {}

    position_bounds = _measure_position_bounds(raw_positions)
    return {
        node_id: _scale_block_point(raw_positions[node_id], position_bounds, scale_spec)
        for node_id in sorted(raw_positions)
    }


def _build_max_node_diameter_units(
    node_ids: Sequence[str],
    node_visual_data: NodeVisualDataMap,
) -> float:
    return max(
        (
            _node_visual_diameter_units(
                _get_node_visual_size(node_visual_data, node_id),
            )
            for node_id in node_ids
        ),
        default=ZERO_FLOAT,
    )


def _build_local_node_cell_span(
    max_node_diameter_units: float,
    layout_tuning: LayoutTuning,
) -> float:
    return max(
        layout_tuning.node_block_cell_span,
        max_node_diameter_units * LAYOUT_POSITION_PADDING_MULTIPLIER + NODE_LAYOUT_CLEARANCE_UNITS,
    )


def _build_local_node_inset(
    max_node_diameter_units: float,
    layout_tuning: LayoutTuning,
) -> float:
    return max(
        layout_tuning.node_layout_inset,
        _half(max_node_diameter_units) + NODE_LAYOUT_OUTER_PADDING_UNITS,
    )


def _build_local_node_layout_sizing(
    ordered_nodes: Sequence[str],
    context: FolderLayoutBuildContext,
) -> LocalNodeLayoutSizing:
    max_node_diameter_units = _build_max_node_diameter_units(
        ordered_nodes,
        context.node_visual_data,
    )
    cell_span = _build_local_node_cell_span(
        max_node_diameter_units,
        context.layout_tuning,
    )
    column_count = max(1, math.ceil(math.sqrt(len(ordered_nodes))))
    return LocalNodeLayoutSizing(
        width=max(
            context.layout_tuning.min_node_block_span,
            float(column_count) * cell_span,
        ),
        height=max(
            context.layout_tuning.min_node_block_span,
            float(math.ceil(len(ordered_nodes) / column_count)) * cell_span,
        ),
        inset=_build_local_node_inset(max_node_diameter_units, context.layout_tuning),
        layout_k_multiplier=max(
            1.0,
            cell_span / max(context.layout_tuning.node_block_cell_span, 1.0),
        ),
    )


def _build_single_node_layout(
    node_id: str,
    layout_sizing: LocalNodeLayoutSizing,
) -> LocalNodeLayout:
    return LocalNodeLayout(
        width=layout_sizing.width,
        height=layout_sizing.height,
        positions={node_id: (_half(layout_sizing.width), _half(layout_sizing.height))},
    )


def _build_multi_node_layout(
    ordered_nodes: Sequence[str],
    context: FolderLayoutBuildContext,
    layout_sizing: LocalNodeLayoutSizing,
) -> LocalNodeLayout:
    subgraph = _build_sorted_layout_subgraph(context.graph, ordered_nodes)
    raw_positions = _normalize_layout_positions(
        cast(
            "Mapping[str, Sequence[float]]",
            nx.spring_layout(
                subgraph,
                k=context.node_layout_k * layout_sizing.layout_k_multiplier,
                iterations=SPRING_LAYOUT_ITERATIONS,
                seed=FREEZE_RANDOM_SEED,
                scale=1,
            ),
        )
    )
    return LocalNodeLayout(
        width=layout_sizing.width,
        height=layout_sizing.height,
        positions=_scale_positions_to_block(
            raw_positions,
            BlockScaleSpec(
                width=layout_sizing.width,
                height=layout_sizing.height,
                inset=layout_sizing.inset,
            ),
        ),
    )


def _build_local_node_layout(
    node_ids: Sequence[str],
    context: FolderLayoutBuildContext,
) -> LocalNodeLayout:
    ordered_nodes = tuple(sorted(node_ids))
    if not ordered_nodes:
        return LocalNodeLayout(width=ZERO_FLOAT, height=ZERO_FLOAT, positions={})

    layout_sizing = _build_local_node_layout_sizing(ordered_nodes, context)
    if len(ordered_nodes) == 1:
        return _build_single_node_layout(ordered_nodes[0], layout_sizing)
    return _build_multi_node_layout(ordered_nodes, context, layout_sizing)


def _build_single_packed_box_layout(
    item_size: tuple[str, float, float],
) -> PackedBoxLayout:
    item_name, item_width, item_height = item_size
    return PackedBoxLayout(
        width=item_width,
        height=item_height,
        origins={item_name: (ZERO_FLOAT, ZERO_FLOAT)},
    )


def _build_packing_grid_shape(item_count: int) -> tuple[int, int]:
    column_count = max(1, math.ceil(math.sqrt(item_count)))
    return (column_count, math.ceil(item_count / column_count))


def _build_packing_column_widths(
    ordered_items: Sequence[tuple[str, float, float]],
    column_count: int,
) -> list[float]:
    return [
        max(
            item_width
            for item_index, (_item_name, item_width, _item_height) in enumerate(ordered_items)
            if item_index % column_count == column_index
        )
        for column_index in range(column_count)
    ]


def _build_packing_row_heights(
    ordered_items: Sequence[tuple[str, float, float]],
    column_count: int,
    row_count: int,
) -> list[float]:
    return [
        max(
            item_height
            for item_index, (_item_name, _item_width, item_height) in enumerate(ordered_items)
            if item_index // column_count == row_index
        )
        for row_index in range(row_count)
    ]


def _build_track_total(track_sizes: Sequence[float], gap_size: float) -> float:
    return sum(track_sizes) + _build_track_gap_total(track_sizes, gap_size)


def _build_track_gap_total(track_sizes: Sequence[float], gap_size: float) -> float:
    return gap_size * max(len(track_sizes) - 1, 0)


def _build_track_offsets(
    track_sizes: Sequence[float],
    gap_size: float,
) -> list[float]:
    offsets: list[float] = []
    current_offset: float = ZERO_FLOAT
    for track_size in track_sizes:
        offsets.append(current_offset)
        current_offset += track_size + gap_size
    return offsets


def _build_row_bottoms(
    row_heights: Sequence[float],
    total_height: float,
    gap_y: float,
) -> list[float]:
    row_offsets = _build_track_offsets(row_heights, gap_y)
    return [
        total_height - row_offsets[row_index] - row_heights[row_index]
        for row_index in range(len(row_heights))
    ]


def _build_packing_frame(
    ordered_items: Sequence[tuple[str, float, float]],
    gap_x: float,
    gap_y: float,
) -> PackedBoxFrame:
    column_count, row_count = _build_packing_grid_shape(len(ordered_items))
    column_widths = _build_packing_column_widths(ordered_items, column_count)
    row_heights = _build_packing_row_heights(ordered_items, column_count, row_count)
    return PackedBoxFrame(
        column_count=column_count,
        total_width=_build_track_total(column_widths, gap_x),
        total_height=_build_track_total(row_heights, gap_y),
        column_widths=column_widths,
        row_heights=row_heights,
    )


def _build_packed_box_origins(
    ordered_items: Sequence[tuple[str, float, float]],
    packing_frame: PackedBoxFrame,
    gap_x: float,
    gap_y: float,
) -> dict[str, tuple[float, float]]:
    packing_offsets = _build_packing_offsets(packing_frame, gap_x, gap_y)
    return {
        item_name: _build_packed_box_origin(
            item_index,
            (item_name, item_width, item_height),
            packing_frame,
            packing_offsets,
        )
        for item_index, (item_name, item_width, item_height) in enumerate(ordered_items)
    }


def _build_packing_offsets(
    packing_frame: PackedBoxFrame,
    gap_x: float,
    gap_y: float,
) -> tuple[list[float], list[float]]:
    return (
        _build_track_offsets(packing_frame.column_widths, gap_x),
        _build_row_bottoms(
            packing_frame.row_heights,
            packing_frame.total_height,
            gap_y,
        ),
    )


def _build_packed_box_origin(
    item_index: int,
    item_size: tuple[str, float, float],
    packing_frame: PackedBoxFrame,
    packing_offsets: tuple[Sequence[float], Sequence[float]],
) -> tuple[float, float]:
    x_offsets, row_bottoms = packing_offsets
    column_index = item_index % packing_frame.column_count
    row_index = item_index // packing_frame.column_count
    return (
        x_offsets[column_index] + _half(packing_frame.column_widths[column_index] - item_size[1]),
        row_bottoms[row_index] + _half(packing_frame.row_heights[row_index] - item_size[2]),
    )


def _build_multi_packed_box_layout(
    ordered_items: Sequence[tuple[str, float, float]],
    gap_x: float,
    gap_y: float,
) -> PackedBoxLayout:
    packing_frame = _build_packing_frame(ordered_items, gap_x, gap_y)
    return PackedBoxLayout(
        width=packing_frame.total_width,
        height=packing_frame.total_height,
        origins=_build_packed_box_origins(ordered_items, packing_frame, gap_x, gap_y),
    )


def _pack_boxes(
    item_sizes: Sequence[tuple[str, float, float]],
    *,
    gap_x: float,
    gap_y: float,
) -> PackedBoxLayout:
    ordered_items = tuple(sorted(item_sizes, key=_named_item_sort_key))
    if not ordered_items:
        return PackedBoxLayout(width=ZERO_FLOAT, height=ZERO_FLOAT, origins={})

    if len(ordered_items) == 1:
        return _build_single_packed_box_layout(ordered_items[0])
    return _build_multi_packed_box_layout(ordered_items, gap_x, gap_y)


def _should_use_side_by_side_sections(
    packed_children: PackedBoxLayout,
    direct_nodes_layout: LocalNodeLayout,
    layout_tuning: LayoutTuning,
) -> bool:
    if not packed_children.width or not direct_nodes_layout.width:
        return False

    combined_area = (
        packed_children.width * packed_children.height
        + direct_nodes_layout.width * direct_nodes_layout.height
    )
    return combined_area >= (layout_tuning.node_block_cell_span**2) * SIDE_BY_SIDE_AREA_THRESHOLD


def _build_child_box_sizes(
    child_names: Sequence[str],
    folder_layouts: Mapping[str, ContainerLayout],
) -> list[tuple[str, float, float]]:
    return [
        (child_name, folder_layouts[child_name].width, folder_layouts[child_name].height)
        for child_name in child_names
    ]


def _build_section_gap(
    primary_height: float,
    secondary_height: float,
    section_gap: float,
) -> float:
    if primary_height and secondary_height:
        return section_gap
    return ZERO_FLOAT


def _build_side_by_side_folder_placement(
    packed_children: PackedBoxLayout,
    direct_nodes_layout: LocalNodeLayout,
    layout_tuning: LayoutTuning,
) -> SectionPlacement:
    section_gap = _build_section_gap(
        packed_children.height,
        direct_nodes_layout.height,
        layout_tuning.folder_section_gap,
    )
    content_width = max(
        layout_tuning.min_folder_content_width,
        packed_children.width + direct_nodes_layout.width + section_gap,
    )
    content_height = max(
        layout_tuning.min_folder_content_height,
        packed_children.height,
        direct_nodes_layout.height,
    )
    child_origin_x = layout_tuning.folder_padding_x + _half(
        content_width - packed_children.width - direct_nodes_layout.width - section_gap,
    )
    return SectionPlacement(
        total_width=content_width,
        total_height=content_height,
        primary_origin=(
            child_origin_x,
            layout_tuning.folder_padding_y + _half(content_height - packed_children.height),
        ),
        secondary_origin=(
            child_origin_x + packed_children.width + section_gap,
            layout_tuning.folder_padding_y + _half(content_height - direct_nodes_layout.height),
        ),
    )


def _build_stacked_folder_placement(
    packed_children: PackedBoxLayout,
    direct_nodes_layout: LocalNodeLayout,
    layout_tuning: LayoutTuning,
) -> SectionPlacement:
    section_gap = _build_section_gap(
        packed_children.height,
        direct_nodes_layout.height,
        layout_tuning.folder_section_gap,
    )
    content_width = max(
        layout_tuning.min_folder_content_width,
        direct_nodes_layout.width,
        packed_children.width,
    )
    content_height = max(
        layout_tuning.min_folder_content_height,
        packed_children.height + direct_nodes_layout.height + section_gap,
    )
    return SectionPlacement(
        total_width=content_width,
        total_height=content_height,
        primary_origin=(
            layout_tuning.folder_padding_x + _half(content_width - packed_children.width),
            layout_tuning.folder_padding_y,
        ),
        secondary_origin=(
            layout_tuning.folder_padding_x + _half(content_width - direct_nodes_layout.width),
            layout_tuning.folder_padding_y + packed_children.height + section_gap,
        ),
    )


def _build_folder_section_placement(
    packed_children: PackedBoxLayout,
    direct_nodes_layout: LocalNodeLayout,
    layout_tuning: LayoutTuning,
) -> SectionPlacement:
    if _should_use_side_by_side_sections(
        packed_children,
        direct_nodes_layout,
        layout_tuning,
    ):
        return _build_side_by_side_folder_placement(
            packed_children,
            direct_nodes_layout,
            layout_tuning,
        )
    return _build_stacked_folder_placement(
        packed_children,
        direct_nodes_layout,
        layout_tuning,
    )


def _offset_layout_positions(
    relative_positions: LayoutPositionMap,
    origin_x: float,
    origin_y: float,
) -> LayoutPositionMap:
    return {
        item_name: (origin_x + local_x, origin_y + local_y)
        for item_name, (local_x, local_y) in relative_positions.items()
    }


def _finalize_folder_container_layout(
    direct_nodes_layout: LocalNodeLayout,
    packed_children: PackedBoxLayout,
    layout_tuning: LayoutTuning,
) -> ContainerLayout:
    section_placement = _build_folder_section_placement(
        packed_children,
        direct_nodes_layout,
        layout_tuning,
    )
    return ContainerLayout(
        width=(
            section_placement.total_width
            + LAYOUT_POSITION_PADDING_MULTIPLIER * layout_tuning.folder_padding_x
        ),
        height=(
            section_placement.total_height
            + LAYOUT_POSITION_PADDING_MULTIPLIER * layout_tuning.folder_padding_y
            + layout_tuning.folder_label_height
        ),
        node_positions=_offset_layout_positions(
            direct_nodes_layout.positions,
            section_placement.secondary_origin[0],
            section_placement.secondary_origin[1],
        ),
        child_origins=_offset_layout_positions(
            packed_children.origins,
            section_placement.primary_origin[0],
            section_placement.primary_origin[1],
        ),
    )


def _build_folder_container_layout(
    folder_name: str,
    folder_layouts: Mapping[str, ContainerLayout],
    context: FolderLayoutBuildContext,
) -> ContainerLayout:
    direct_nodes_layout = _build_local_node_layout(
        context.folder_to_nodes.get(folder_name, ()),
        context,
    )
    child_box_sizes = _build_child_box_sizes(
        tuple(sorted(context.child_folders.get(folder_name, ()))),
        folder_layouts,
    )
    packed_children = _pack_boxes(
        child_box_sizes,
        gap_x=context.layout_tuning.folder_grid_gap_x,
        gap_y=context.layout_tuning.folder_grid_gap_y,
    )
    return _finalize_folder_container_layout(
        direct_nodes_layout,
        packed_children,
        context.layout_tuning,
    )


def _build_root_child_sizes(
    root_folders: Sequence[str],
    folder_layouts: Mapping[str, ContainerLayout],
) -> list[tuple[str, float, float]]:
    return [
        (folder_name, folder_layouts[folder_name].width, folder_layouts[folder_name].height)
        for folder_name in sorted(root_folders)
    ]


def _build_side_by_side_root_placement(
    packed_root_folders: PackedBoxLayout,
    root_nodes_layout: LocalNodeLayout,
    root_section_gap: float,
) -> SectionPlacement:
    total_height = max(packed_root_folders.height, root_nodes_layout.height)
    return SectionPlacement(
        total_width=packed_root_folders.width + root_nodes_layout.width + root_section_gap,
        total_height=total_height,
        primary_origin=(ZERO_FLOAT, _half(total_height - packed_root_folders.height)),
        secondary_origin=(
            packed_root_folders.width + root_section_gap,
            _half(total_height - root_nodes_layout.height),
        ),
    )


def _build_stacked_root_placement(
    packed_root_folders: PackedBoxLayout,
    root_nodes_layout: LocalNodeLayout,
    root_section_gap: float,
) -> SectionPlacement:
    total_width = max(root_nodes_layout.width, packed_root_folders.width)
    return SectionPlacement(
        total_width=total_width,
        total_height=packed_root_folders.height + root_nodes_layout.height + root_section_gap,
        primary_origin=(_half(total_width - packed_root_folders.width), ZERO_FLOAT),
        secondary_origin=(
            _half(total_width - root_nodes_layout.width),
            packed_root_folders.height + root_section_gap,
        ),
    )


def _build_root_section_placement(
    packed_root_folders: PackedBoxLayout,
    root_nodes_layout: LocalNodeLayout,
    layout_tuning: LayoutTuning,
) -> SectionPlacement:
    root_section_gap = _build_section_gap(
        packed_root_folders.height,
        root_nodes_layout.height,
        layout_tuning.root_section_gap,
    )
    if _should_use_side_by_side_sections(
        packed_root_folders,
        root_nodes_layout,
        layout_tuning,
    ):
        return _build_side_by_side_root_placement(
            packed_root_folders,
            root_nodes_layout,
            root_section_gap,
        )
    return _build_stacked_root_placement(
        packed_root_folders,
        root_nodes_layout,
        root_section_gap,
    )


def _finalize_root_container_layout(
    root_nodes_layout: LocalNodeLayout,
    packed_root_folders: PackedBoxLayout,
    layout_tuning: LayoutTuning,
) -> ContainerLayout:
    section_placement = _build_root_section_placement(
        packed_root_folders,
        root_nodes_layout,
        layout_tuning,
    )
    return ContainerLayout(
        width=section_placement.total_width,
        height=section_placement.total_height,
        node_positions=_offset_layout_positions(
            root_nodes_layout.positions,
            section_placement.secondary_origin[0],
            section_placement.secondary_origin[1],
        ),
        child_origins=_offset_layout_positions(
            packed_root_folders.origins,
            section_placement.primary_origin[0],
            section_placement.primary_origin[1],
        ),
    )


def _build_root_container_layout(
    root_folder_nodes: Sequence[str],
    root_folders: Sequence[str],
    folder_layouts: Mapping[str, ContainerLayout],
    context: FolderLayoutBuildContext,
) -> ContainerLayout:
    root_nodes_layout = _build_local_node_layout(
        root_folder_nodes,
        context,
    )
    root_child_sizes = _build_root_child_sizes(root_folders, folder_layouts)
    packed_root_folders = _pack_boxes(
        root_child_sizes,
        gap_x=context.layout_tuning.folder_grid_gap_x,
        gap_y=context.layout_tuning.folder_grid_gap_y,
    )
    return _finalize_root_container_layout(
        root_nodes_layout,
        packed_root_folders,
        context.layout_tuning,
    )


def _build_folder_rect_data() -> FolderRectData:
    return FolderRectData()


def _assign_layout_node_positions(
    origin_x: float,
    origin_y: float,
    layout: ContainerLayout,
    final_positions: LayoutPositionMap,
) -> None:
    for node_id in sorted(layout.node_positions):
        relative_x, relative_y = layout.node_positions[node_id]
        final_positions[node_id] = (origin_x + relative_x, origin_y + relative_y)


def _assign_child_layout_positions(
    origin_x: float,
    origin_y: float,
    layout: ContainerLayout,
    assignment: FolderPositionAssignment,
) -> None:
    for child_name in sorted(layout.child_origins):
        child_origin_x, child_origin_y = layout.child_origins[child_name]
        _assign_folder_positions(
            child_name,
            origin_x + child_origin_x,
            origin_y + child_origin_y,
            assignment,
        )


def _assign_folder_positions(
    folder_name: str,
    origin_x: float,
    origin_y: float,
    assignment: FolderPositionAssignment,
) -> None:
    layout = assignment.folder_layouts[folder_name]
    assignment.folder_rect_data.append_folder(
        folder_name,
        origin_x,
        origin_y,
        layout,
        assignment.layout_tuning,
    )
    _assign_layout_node_positions(origin_x, origin_y, layout, assignment.final_positions)
    _assign_child_layout_positions(origin_x, origin_y, layout, assignment)


def _append_layout_bounds(
    horizontal_bounds: list[tuple[float, float]],
    vertical_bounds: list[tuple[float, float]],
    horizontal_range: tuple[float, float],
    vertical_range: tuple[float, float],
) -> None:
    horizontal_bounds.append(horizontal_range)
    vertical_bounds.append(vertical_range)


def _build_node_layout_bounds(
    final_positions: LayoutPositionMap,
    node_visual_data: NodeVisualDataMap,
    horizontal_bounds: list[tuple[float, float]],
    vertical_bounds: list[tuple[float, float]],
) -> None:
    for node_id, (x_coord, y_coord) in final_positions.items():
        node_radius = _node_visual_radius_units(
            _get_node_visual_size(node_visual_data, node_id),
        )
        _append_layout_bounds(
            horizontal_bounds,
            vertical_bounds,
            (x_coord - node_radius, x_coord + node_radius),
            (y_coord - node_radius, y_coord + node_radius),
        )


def _build_folder_layout_bounds(
    folder_rect_data: FolderRectData,
    horizontal_bounds: list[tuple[float, float]],
    vertical_bounds: list[tuple[float, float]],
) -> None:
    for center_x, center_y, width, height in zip(
        folder_rect_data.center_xs,
        folder_rect_data.center_ys,
        folder_rect_data.widths,
        folder_rect_data.heights,
        strict=True,
    ):
        _append_layout_bounds(
            horizontal_bounds,
            vertical_bounds,
            (center_x - _half(width), center_x + _half(width)),
            (center_y - _half(height), center_y + _half(height)),
        )


def _empty_layout_bounds() -> LayoutBounds:
    return LayoutBounds(
        min_x=ZERO_FLOAT,
        max_x=ZERO_FLOAT,
        min_y=ZERO_FLOAT,
        max_y=ZERO_FLOAT,
    )


def _build_measured_layout_bounds(
    horizontal_bounds: Sequence[tuple[float, float]],
    vertical_bounds: Sequence[tuple[float, float]],
) -> LayoutBounds:
    return LayoutBounds(
        min_x=min(lower_bound for lower_bound, _ in horizontal_bounds),
        max_x=max(upper_bound for _, upper_bound in horizontal_bounds),
        min_y=min(lower_bound for lower_bound, _ in vertical_bounds),
        max_y=max(upper_bound for _, upper_bound in vertical_bounds),
    )


def _build_folder_layout_source_data(graph: nx.DiGraph) -> FolderLayoutSourceData:
    folder_to_nodes, root_folder_nodes = _collect_folder_nodes(graph)
    folder_hierarchy = _build_folder_hierarchy(folder_to_nodes)
    return FolderLayoutSourceData(
        folder_to_nodes=folder_to_nodes,
        root_folder_nodes=root_folder_nodes,
        root_folders=folder_hierarchy[0],
        child_folders=folder_hierarchy[1],
    )


def _build_folder_layouts(
    source_data: FolderLayoutSourceData,
    build_context: FolderLayoutBuildContext,
) -> dict[str, ContainerLayout]:
    folder_layouts: dict[str, ContainerLayout] = {}
    for folder_name in sorted(
        source_data.folder_to_nodes,
        key=_folder_depth_sort_key,
        reverse=True,
    ):
        folder_layouts[folder_name] = _build_folder_container_layout(
            folder_name,
            folder_layouts,
            build_context,
        )
    return folder_layouts


def _build_constrained_layout_data(
    graph: nx.DiGraph,
    node_visual_data: NodeVisualDataMap,
) -> ConstrainedLayoutData:
    source_data = _build_folder_layout_source_data(graph)
    layout_tuning = _build_layout_tuning(graph, source_data.folder_to_nodes)
    build_context = FolderLayoutBuildContext(
        graph=graph,
        folder_to_nodes=source_data.folder_to_nodes,
        child_folders=source_data.child_folders,
        node_layout_k=DEFAULT_NODE_LAYOUT_K,
        layout_tuning=layout_tuning,
        node_visual_data=node_visual_data,
    )
    return ConstrainedLayoutData(
        source_data=source_data,
        build_context=build_context,
        folder_layouts=_build_folder_layouts(source_data, build_context),
    )


def _build_root_final_positions(root_layout: ContainerLayout) -> LayoutPositionMap:
    return {
        node_id: (
            relative_x - _half(root_layout.width),
            relative_y - _half(root_layout.height),
        )
        for node_id, (relative_x, relative_y) in root_layout.node_positions.items()
    }


def _build_folder_position_assignment(
    folder_layouts: Mapping[str, ContainerLayout],
    final_positions: LayoutPositionMap,
    layout_tuning: LayoutTuning,
) -> FolderPositionAssignment:
    return FolderPositionAssignment(
        folder_layouts=folder_layouts,
        folder_rect_data=_build_folder_rect_data(),
        final_positions=final_positions,
        layout_tuning=layout_tuning,
    )


def _assign_root_child_folder_positions(
    root_layout: ContainerLayout,
    assignment: FolderPositionAssignment,
) -> None:
    root_origin_x = -_half(root_layout.width)
    root_origin_y = -_half(root_layout.height)
    for folder_name in sorted(root_layout.child_origins):
        child_origin_x, child_origin_y = root_layout.child_origins[folder_name]
        _assign_folder_positions(
            folder_name,
            root_origin_x + child_origin_x,
            root_origin_y + child_origin_y,
            assignment,
        )


def _create_constrained_layout(
    graph: nx.DiGraph,
    node_visual_data: NodeVisualDataMap,
) -> tuple[LayoutPositionMap, FolderRectData]:
    constrained_layout_data = _build_constrained_layout_data(graph, node_visual_data)
    root_layout = _build_root_container_layout(
        constrained_layout_data.source_data.root_folder_nodes,
        constrained_layout_data.source_data.root_folders,
        constrained_layout_data.folder_layouts,
        constrained_layout_data.build_context,
    )
    final_positions = _build_root_final_positions(root_layout)
    assignment = _build_folder_position_assignment(
        constrained_layout_data.folder_layouts,
        final_positions=final_positions,
        layout_tuning=constrained_layout_data.build_context.layout_tuning,
    )
    _assign_root_child_folder_positions(root_layout, assignment)
    return final_positions, assignment.folder_rect_data


def _measure_layout_bounds(
    final_positions: LayoutPositionMap,
    folder_rect_data: FolderRectData,
    node_visual_data: NodeVisualDataMap,
) -> LayoutBounds:
    horizontal_bounds: list[tuple[float, float]] = []
    vertical_bounds: list[tuple[float, float]] = []
    _build_node_layout_bounds(
        final_positions,
        node_visual_data,
        horizontal_bounds,
        vertical_bounds,
    )
    _build_folder_layout_bounds(
        folder_rect_data,
        horizontal_bounds,
        vertical_bounds,
    )

    if not horizontal_bounds or not vertical_bounds:
        return _empty_layout_bounds()
    return _build_measured_layout_bounds(horizontal_bounds, vertical_bounds)


def _build_plot_complexity_dimensions(
    render_data: PreparedBokehRender,
) -> tuple[int, int]:
    node_count = len(render_data.final_positions)
    folder_count = render_data.folder_rect_data.folder_count
    max_node_size = max(
        (visual_data["viz_size"] for visual_data in render_data.node_visual_data.values()),
        default=MIN_NODE_SIZE,
    )
    node_size_budget = max(max_node_size - MIN_NODE_SIZE, 0)
    return (
        BASE_PLOT_WIDTH
        + max(node_count - PLOT_NODE_COMPLEXITY_THRESHOLD, 0) * PLOT_WIDTH_NODE_STEP
        + max(folder_count - PLOT_FOLDER_COMPLEXITY_THRESHOLD, 0) * PLOT_WIDTH_FOLDER_STEP
        + node_size_budget * PLOT_WIDTH_NODE_SIZE_STEP,
        BASE_PLOT_HEIGHT
        + max(node_count - PLOT_NODE_COMPLEXITY_THRESHOLD, 0) * PLOT_HEIGHT_NODE_STEP
        + max(folder_count - PLOT_FOLDER_COMPLEXITY_THRESHOLD, 0) * PLOT_HEIGHT_FOLDER_STEP
        + node_size_budget * PLOT_HEIGHT_NODE_SIZE_STEP,
    )


def _build_plot_dimensions(render_data: PreparedBokehRender) -> PlotDimensions:
    layout_bounds = _measure_layout_bounds(
        render_data.final_positions,
        render_data.folder_rect_data,
        render_data.node_visual_data,
    )
    complexity_width, complexity_height = _build_plot_complexity_dimensions(render_data)
    width = math.ceil(
        _clamp_float(
            max(layout_bounds.width * PLOT_PIXELS_PER_LAYOUT_UNIT, float(complexity_width)),
            BASE_PLOT_WIDTH,
            MAX_PLOT_WIDTH,
        )
    )
    height = math.ceil(
        _clamp_float(
            max(layout_bounds.height * PLOT_PIXELS_PER_LAYOUT_UNIT, float(complexity_height)),
            BASE_PLOT_HEIGHT,
            MAX_PLOT_HEIGHT,
        )
    )
    return PlotDimensions(width=width, height=height)


def _build_empty_plot_ranges() -> tuple[bokeh_models.Range1d, bokeh_models.Range1d]:
    return (
        bokeh_models.Range1d(start=-EMPTY_PLOT_RANGE_EXTENT, end=EMPTY_PLOT_RANGE_EXTENT),
        bokeh_models.Range1d(start=-EMPTY_PLOT_RANGE_EXTENT, end=EMPTY_PLOT_RANGE_EXTENT),
    )


def _build_padded_layout_size(layout_bounds: LayoutBounds) -> PaddedLayoutSize:
    padding_x = max(
        INITIAL_VIEW_MIN_PADDING_UNITS,
        LAYOUT_VIEWPORT_PADDING_UNITS,
        layout_bounds.width * INITIAL_VIEW_PADDING_FRACTION,
    )
    padding_y = max(
        INITIAL_VIEW_MIN_PADDING_UNITS,
        LAYOUT_VIEWPORT_PADDING_UNITS,
        layout_bounds.height * INITIAL_VIEW_PADDING_FRACTION,
    )
    return PaddedLayoutSize(
        width=max(
            layout_bounds.width + LAYOUT_POSITION_PADDING_MULTIPLIER * padding_x,
            1.0,
        ),
        height=max(
            layout_bounds.height + LAYOUT_POSITION_PADDING_MULTIPLIER * padding_y,
            1.0,
        ),
    )


def _build_plot_view_half_spans(
    padded_layout_size: PaddedLayoutSize,
    plot_dimensions: PlotDimensions,
) -> tuple[float, float]:
    plot_aspect_ratio = max(
        float(plot_dimensions.width) / max(float(plot_dimensions.height), 1.0),
        MIN_PLOT_ASPECT_RATIO,
    )
    if padded_layout_size.width / padded_layout_size.height > plot_aspect_ratio:
        return (
            _half(padded_layout_size.width) * INITIAL_VIEW_SAFETY_SCALE,
            _half(padded_layout_size.width / plot_aspect_ratio) * INITIAL_VIEW_SAFETY_SCALE,
        )
    return (
        _half(padded_layout_size.height * plot_aspect_ratio) * INITIAL_VIEW_SAFETY_SCALE,
        _half(padded_layout_size.height) * INITIAL_VIEW_SAFETY_SCALE,
    )


def _build_layout_center(layout_bounds: LayoutBounds) -> tuple[float, float]:
    return (
        _half(layout_bounds.min_x + layout_bounds.max_x),
        _half(layout_bounds.min_y + layout_bounds.max_y),
    )


def _build_centered_plot_ranges(
    layout_bounds: LayoutBounds,
    padded_layout_size: PaddedLayoutSize,
    plot_dimensions: PlotDimensions,
) -> tuple[bokeh_models.Range1d, bokeh_models.Range1d]:
    center_position = _build_layout_center(layout_bounds)
    half_spans = _build_plot_view_half_spans(padded_layout_size, plot_dimensions)
    return (
        bokeh_models.Range1d(
            start=center_position[0] - half_spans[0],
            end=center_position[0] + half_spans[0],
        ),
        bokeh_models.Range1d(
            start=center_position[1] - half_spans[1],
            end=center_position[1] + half_spans[1],
        ),
    )


def _build_plot_ranges(
    render_data: PreparedBokehRender,
    plot_dimensions: PlotDimensions,
) -> tuple[bokeh_models.Range1d, bokeh_models.Range1d]:
    layout_bounds = _measure_layout_bounds(
        render_data.final_positions,
        render_data.folder_rect_data,
        render_data.node_visual_data,
    )
    if not layout_bounds.width and not layout_bounds.height:
        return _build_empty_plot_ranges()

    return _build_centered_plot_ranges(
        layout_bounds,
        _build_padded_layout_size(layout_bounds),
        plot_dimensions,
    )


def _build_bokeh_layout(
    graph: nx.DiGraph,
    layout: str,
    node_visual_data: NodeVisualDataMap,
) -> tuple[LayoutPositionMap, FolderRectData]:
    if layout != "constrained":
        raise ValueError(f"Unsupported Bokeh layout '{layout}'. Supported layouts: constrained.")

    return _create_constrained_layout(graph, node_visual_data)


def _build_node_visual_data(graph: nx.DiGraph) -> MutableNodeVisualDataMap:
    degrees = dict(graph.degree())
    node_count = graph.number_of_nodes()
    visual_data: MutableNodeVisualDataMap = {}

    for node_id in sorted(graph.nodes(), key=str):
        visual_data[node_id] = _build_single_node_visual_data(
            graph.nodes[node_id],
            node_id,
            degrees.get(node_id, 0),
            node_count,
        )

    return visual_data


def _build_single_node_visual_data(
    node_data: Mapping[str, object],
    node_id: object,
    current_degree: int,
    node_count: int,
) -> NodeVisualData:
    calculated_size = _calculate_node_visual_size(current_degree, node_count)
    return NodeVisualData(
        viz_size=calculated_size,
        viz_color=COLOR_MAP.get(
            str(node_data.get("type", "unresolved")),
            DEFAULT_NODE_COLOR,
        ),
        viz_label=str(node_data.get("label", node_id)),
        viz_degree=current_degree,
        viz_type=str(node_data.get("type", "unresolved")),
        viz_label_y_offset=int(_half(float(calculated_size)) + LABEL_PADDING),
        in_degree=_to_int(node_data.get("in_degree", 0)),
        out_degree=_to_int(node_data.get("out_degree", 0)),
        total_degree=_to_int(node_data.get("total_degree", 0)),
    )


def _copy_sorted_graph_structure(graph: nx.DiGraph) -> nx.DiGraph:
    graph_to_draw = nx.DiGraph()
    for node_id, node_data in sorted(graph.nodes(data=True), key=_node_item_sort_key):
        graph_to_draw.add_node(node_id, **dict(node_data))
    for start_node, end_node in sorted(graph.edges(), key=_edge_sort_key):
        graph_to_draw.add_edge(start_node, end_node)
    return graph_to_draw


def _copy_graph_with_visual_data(
    graph: nx.DiGraph,
    node_visual_data: NodeVisualDataMap,
) -> nx.DiGraph:
    graph_to_draw = _copy_sorted_graph_structure(graph)
    for node_id, visual_data in node_visual_data.items():
        graph_to_draw.nodes[node_id].update(visual_data)

    return graph_to_draw


def _to_int(raw_value: object) -> int:
    if isinstance(raw_value, bool):
        return int(raw_value)
    if isinstance(raw_value, int):
        return raw_value
    return 0


def _build_edge_visual_style(graph: nx.DiGraph) -> EdgeVisualStyle:
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    if (
        node_count >= COMPACT_GRAPH_NODE_COUNT_THRESHOLD
        or edge_count >= COMPACT_EDGE_COUNT_THRESHOLD
    ):
        return COMPACT_EDGE_STYLE
    if node_count >= MEDIUM_GRAPH_NODE_COUNT_THRESHOLD or edge_count >= MEDIUM_EDGE_COUNT_THRESHOLD:
        return MEDIUM_EDGE_STYLE
    return DEFAULT_EDGE_STYLE


def _build_render_policy(graph: nx.DiGraph) -> RenderPolicy:
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    dense_graph = node_count >= LOD_RENDER_NODE_THRESHOLD or edge_count >= LOD_RENDER_EDGE_THRESHOLD
    return RenderPolicy(
        # Use a single canvas backend so browser rendering stays consistent.
        output_backend="canvas",
        show_arrows=not (
            node_count >= ARROW_RENDER_NODE_THRESHOLD or edge_count >= ARROW_RENDER_EDGE_THRESHOLD
        ),
        lod_threshold=1 if dense_graph else None,
        lod_factor=LOD_FACTOR,
        lod_interval=LOD_INTERVAL_MS,
        lod_timeout=LOD_TIMEOUT_MS,
    )


def _build_toolbar_stylesheet() -> bokeh_models.InlineStyleSheet:
    return bokeh_models.InlineStyleSheet(
        css=(
            ":host {"
            f" --button-width: {TOOLBAR_BUTTON_WIDTH_PX}px;"
            f" --button-height: {TOOLBAR_BUTTON_HEIGHT_PX}px;"
            " position: fixed;"
            f" left: {TOOLBAR_VIEWPORT_LEFT_PX}px;"
            f" top: {TOOLBAR_VIEWPORT_TOP_PX}px;"
            " z-index: 1000;"
            " padding: 6px;"
            " border-radius: 12px;"
            " border: 1px solid rgba(15, 23, 42, 0.14);"
            " background: rgba(255, 255, 255, 0.94);"
            " box-shadow: 0 12px 28px rgba(15, 23, 42, 0.18);"
            " backdrop-filter: blur(8px);"
            " }"
            " .bk-tool-icon {"
            f" mask-size: {TOOLBAR_ICON_SCALE_PERCENT}% {TOOLBAR_ICON_SCALE_PERCENT}%;"
            f" -webkit-mask-size: {TOOLBAR_ICON_SCALE_PERCENT}% {TOOLBAR_ICON_SCALE_PERCENT}%;"
            f" background-size: {TOOLBAR_ICON_SCALE_PERCENT}% {TOOLBAR_ICON_SCALE_PERCENT}%;"
            " }"
            " .bk-divider {"
            " opacity: 0.35;"
            " }"
        )
    )


def _configure_plot_tools(
    plot: bokeh_plotting.figure,
) -> tuple[bokeh_models.PanTool, bokeh_models.HoverTool]:
    pan_tool = bokeh_models.PanTool()
    hover_tool = bokeh_models.HoverTool(visible=False)
    plot.add_tools(
        pan_tool,
        bokeh_models.WheelZoomTool(maintain_focus=False, visible=False),
        bokeh_models.ZoomInTool(),
        bokeh_models.ZoomOutTool(),
        bokeh_models.BoxZoomTool(),
        bokeh_models.ResetTool(),
        bokeh_models.SaveTool(),
        bokeh_models.TapTool(visible=False),
        hover_tool,
    )
    return pan_tool, hover_tool


def _add_folder_overlays(
    plot: bokeh_plotting.figure,
    folder_rect_data: FolderRectData,
) -> bokeh_models.ColumnDataSource:
    folder_source = bokeh_models.ColumnDataSource(data=folder_rect_data.as_column_data())
    plot.rect(
        x=FOLDER_X_FIELD,
        y=FOLDER_Y_FIELD,
        width=FOLDER_WIDTH_FIELD,
        height=FOLDER_HEIGHT_FIELD,
        source=folder_source,
        fill_color=FOLDER_COLOR_FIELD,
        fill_alpha=FOLDER_RECT_FILL_ALPHA,
        line_color=BLACK_COLOR,
        line_dash="dashed",
        level="underlay",
    )
    plot.add_layout(
        _BOKEH_MODELS_ANY.LabelSet(
            x=FOLDER_X_FIELD,
            y=FOLDER_LABEL_Y_FIELD,
            text=FOLDER_NAME_FIELD,
            source=folder_source,
            text_font_size="12pt",
            text_color=BLACK_COLOR,
            text_align="center",
            y_offset=0,
            level="overlay",
        )
    )
    return folder_source


def _create_bokeh_plot(
    folder_rect_data: FolderRectData,
    plot_dimensions: PlotDimensions,
    plot_ranges: tuple[bokeh_models.Range1d, bokeh_models.Range1d],
    render_policy: RenderPolicy,
) -> tuple[bokeh_plotting.figure, bokeh_models.ColumnDataSource]:
    plot = bokeh_plotting.figure(title=INTERACTIVE_PLOT_TITLE)
    plot.output_backend = render_policy.output_backend
    plot.width = plot_dimensions.width
    plot.height = plot_dimensions.height
    plot.x_range = plot_ranges[0]
    plot.y_range = plot_ranges[1]
    plot.toolbar_location = "left"
    plot.toolbar_inner = True
    plot.toolbar_sticky = True
    plot.toolbar.tools = []
    plot.toolbar.logo = None
    plot.toolbar.autohide = False
    plot.toolbar.stylesheets = [_build_toolbar_stylesheet()]
    plot.match_aspect = True
    plot.lod_threshold = render_policy.lod_threshold
    plot.lod_factor = render_policy.lod_factor
    plot.lod_interval = render_policy.lod_interval
    plot.lod_timeout = render_policy.lod_timeout

    pan_tool, hover_tool = _configure_plot_tools(plot)
    plot.toolbar.active_drag = pan_tool
    plot.toolbar.active_inspect = hover_tool

    return plot, _add_folder_overlays(plot, folder_rect_data)


def _get_graph_renderer_node_data(
    graph_renderer: _GraphRendererLike,
) -> Mapping[str, object]:
    node_renderer = cast("_BokehRendererLayer", graph_renderer.node_renderer)
    data_source = node_renderer.data_source
    return cast("Mapping[str, object]", data_source.data)


def _build_ordered_renderer_node_ids(
    node_data: Mapping[str, object],
) -> list[str] | None:
    indices = node_data.get("index")
    if not isinstance(indices, list) or not indices:
        return None
    return [str(node_id) for node_id in indices]


def _apply_synced_node_coordinates(
    node_data: Mapping[str, object],
    synced_coordinates: tuple[list[float], list[float]],
) -> None:
    node_xs, node_ys = synced_coordinates
    mutable_node_data = cast("dict[str, object]", node_data)
    mutable_node_data["x"] = node_xs
    mutable_node_data["y"] = node_ys


def _sync_node_coordinates(
    graph_renderer: _GraphRendererLike,
    final_positions: LayoutPositionMap,
) -> None:
    node_data = _get_graph_renderer_node_data(graph_renderer)
    if _node_coordinates_are_already_synced(node_data):
        return

    ordered_node_ids = _build_ordered_renderer_node_ids(node_data)
    if ordered_node_ids is None:
        return
    synced_coordinates = _build_synced_node_coordinates(ordered_node_ids, final_positions)
    if synced_coordinates is None:
        return
    _apply_synced_node_coordinates(node_data, synced_coordinates)


def _configure_node_renderer(graph_renderer: _GraphRendererLike) -> None:
    node_renderer = cast("_BokehRendererLayer", graph_renderer.node_renderer)
    node_renderer.glyph = bokeh_models.Scatter(
        marker="circle",
        size=VIZ_SIZE_FIELD,
        fill_color="viz_color",
        fill_alpha=NODE_FILL_ALPHA,
        line_color=BLACK_COLOR,
        line_width=0.5,
    )
    node_renderer.hover_glyph = bokeh_models.Scatter(
        marker="circle",
        size=VIZ_SIZE_FIELD,
        fill_color="orange",
        fill_alpha=NODE_FILL_ALPHA,
        line_color=BLACK_COLOR,
        line_width=2,
    )
    node_renderer.selection_glyph = bokeh_models.Scatter(
        marker="circle",
        size=VIZ_SIZE_FIELD,
        fill_color="firebrick",
        fill_alpha=NODE_FILL_ALPHA,
        line_color=BLACK_COLOR,
        line_width=2,
    )


def _node_coordinates_are_already_synced(node_data: Mapping[str, object]) -> bool:
    return isinstance(node_data.get(FOLDER_X_FIELD), list) and isinstance(
        node_data.get(FOLDER_Y_FIELD),
        list,
    )


def _build_synced_node_coordinates(
    ordered_node_ids: Sequence[str],
    final_positions: LayoutPositionMap,
) -> tuple[list[float], list[float]] | None:
    try:
        return (
            [final_positions[node_id][0] for node_id in ordered_node_ids],
            [final_positions[node_id][1] for node_id in ordered_node_ids],
        )
    except KeyError:
        return None


def _configure_edge_renderer(
    graph_renderer: _GraphRendererLike,
    edge_style: EdgeVisualStyle,
) -> None:
    edge_renderer = cast("_BokehRendererLayer", graph_renderer.edge_renderer)
    edge_renderer.glyph = bokeh_models.MultiLine(
        line_color="#CCCCCC",
        line_alpha=edge_style.line_alpha,
        line_width=edge_style.line_width,
    )
    edge_renderer.hover_glyph = bokeh_models.MultiLine(
        line_color="orange",
        line_alpha=EDGE_HOVER_LINE_ALPHA,
        line_width=2,
    )
    edge_renderer.selection_glyph = bokeh_models.MultiLine(
        line_color="firebrick",
        line_alpha=EDGE_SELECTION_LINE_ALPHA,
        line_width=2,
    )


def _append_arrow_coordinates(
    arrow_source_data: ArrowSourceData,
    final_positions: LayoutPositionMap,
    start_node: str,
    end_node: str,
) -> None:
    start_coords = final_positions[start_node]
    end_coords = final_positions[end_node]
    arrow_source_data["start_x"].append(start_coords[0])
    arrow_source_data["start_y"].append(start_coords[1])
    arrow_source_data["end_x"].append(end_coords[0])
    arrow_source_data["end_y"].append(end_coords[1])


def _build_arrow_source_data(
    graph: nx.DiGraph,
    final_positions: LayoutPositionMap,
) -> ArrowSourceData:
    arrow_source_data: ArrowSourceData = {
        "start_x": [],
        "start_y": [],
        "end_x": [],
        "end_y": [],
    }
    for start_node, end_node in sorted(graph.edges(), key=_edge_sort_key):
        _append_arrow_coordinates(
            arrow_source_data,
            final_positions,
            str(start_node),
            str(end_node),
        )

    return arrow_source_data


def _add_arrow_renderer(
    plot: bokeh_plotting.figure,
    arrow_source_data: ArrowSourceData,
    edge_style: EdgeVisualStyle,
) -> None:
    arrow_source = bokeh_models.ColumnDataSource(data=arrow_source_data)
    arrow_renderer = _BOKEH_MODELS_ANY.Arrow(
        end=_BOKEH_MODELS_ANY.OpenHead(
            line_color="gray",
            line_alpha=edge_style.arrow_alpha,
            line_width=edge_style.arrow_line_width,
            size=edge_style.arrow_head_size,
        ),
        source=arrow_source,
        x_start="start_x",
        y_start="start_y",
        x_end="end_x",
        y_end="end_y",
    )
    arrow_renderer_any = cast("Any", arrow_renderer)
    arrow_renderer_any.update(
        line_alpha=edge_style.arrow_alpha,
        line_width=edge_style.arrow_line_width,
    )
    plot.add_layout(arrow_renderer)


def _configure_hover(
    plot: bokeh_plotting.figure,
    graph_renderer: _GraphRendererLike,
) -> None:
    hover_tool = cast(
        "bokeh_models.HoverTool | None",
        plot.select_one({"type": bokeh_models.HoverTool}),
    )
    if hover_tool is None:
        return

    hover_renderer = cast("Any", graph_renderer.node_renderer)
    hover_tool.renderers = [hover_renderer]
    hover_tool.tooltips = [
        ("Name", "@viz_label"),
        ("Type", "@viz_type"),
        ("Total Links", "@total_degree"),
        ("Incoming", "@in_degree"),
        ("Outgoing", "@out_degree"),
        ("ID", "@index"),
        ("Folder", "@folder"),
    ]


def _build_bokeh_output_path() -> Path:
    with tempfile.NamedTemporaryFile(
        prefix=BOKEH_OUTPUT_PREFIX,
        suffix=BOKEH_OUTPUT_SUFFIX,
        delete=False,
    ) as file_handle:
        return Path(file_handle.name)


def _save_plot(plot: bokeh_plotting.figure) -> Path:
    output_path = _build_bokeh_output_path()
    bokeh_io.save(
        plot,
        filename=output_path,
        resources=bokeh_resources.CDN,
        title=BOKEH_PLOT_TITLE,
    )
    return output_path


def _build_auto_open_uri(output_path: Path) -> str | None:
    """Return a safe file URI for an auto-openable generated plot."""
    try:
        resolved_output_path = output_path.resolve(strict=True)
    except OSError:
        return None

    if not resolved_output_path.is_file():
        return None
    if not resolved_output_path.name.startswith(BOKEH_OUTPUT_PREFIX):
        return None
    if resolved_output_path.suffix.lower() != BOKEH_OUTPUT_SUFFIX:
        return None

    return resolved_output_path.as_uri()


def _should_skip_auto_open(controller: object) -> bool:
    return controller.__class__.__name__ in SKIPPED_AUTO_OPEN_CONTROLLER_NAMES


def get_browser_controller(browser: str | None = None) -> object:
    """Expose browser-controller lookup for runtime use and tests."""
    if browser is None:
        return webbrowser.get()
    return webbrowser.get(browser)


def _open_saved_plot(output_path: Path) -> bool:
    output_uri = _build_auto_open_uri(output_path)
    if output_uri is None:
        return False

    try:
        controller = get_browser_controller(None)
    except (OSError, webbrowser.Error):
        return False
    if _should_skip_auto_open(controller):
        return False

    try:
        return _open_browser_controller(
            cast("webbrowser.BaseBrowser", controller),
            output_uri,
        )
    except (OSError, webbrowser.Error):
        return False


def _open_browser_controller(
    controller: webbrowser.BaseBrowser,
    output_uri: str,
) -> bool:
    return bool(controller.open(output_uri, new=2, autoraise=True))


def _build_manual_open_message(output_path: Path) -> str:
    return (
        "Interactive dependency graph saved to "
        f"{output_path}. Automatic browser launch is unavailable in this environment; "
        "open the file manually."
    )


def _present_plot(plot: bokeh_plotting.figure) -> str | None:
    output_path = _save_plot(plot)
    if _open_saved_plot(output_path):
        return None
    return _build_manual_open_message(output_path)


def _build_plot_for_render(
    render_data: PreparedBokehRender,
    render_policy: RenderPolicy,
) -> bokeh_plotting.figure:
    plot_dimensions = _build_plot_dimensions(render_data)
    plot, _folder_source = _create_bokeh_plot(
        render_data.folder_rect_data,
        plot_dimensions,
        _build_plot_ranges(render_data, plot_dimensions),
        render_policy,
    )
    return plot


def _render_graph_on_plot(
    graph_to_draw: nx.DiGraph,
    render_data: PreparedBokehRender,
    edge_style: EdgeVisualStyle,
    plot: bokeh_plotting.figure,
    *,
    show_arrows: bool,
) -> None:
    graph_renderer = bokeh_plotting.from_networkx(
        graph_to_draw,
        cast("dict[int | str, Sequence[float]]", render_data.final_positions),
    )
    _sync_node_coordinates(graph_renderer, render_data.final_positions)
    _configure_node_renderer(graph_renderer)
    _configure_edge_renderer(graph_renderer, edge_style)
    if show_arrows:
        _add_arrow_renderer(plot, render_data.arrow_source_data, edge_style)
    graph_renderer.selection_policy = bokeh_models.NodesAndLinkedEdges()
    graph_renderer.inspection_policy = bokeh_models.NodesAndLinkedEdges()
    _configure_hover(plot, graph_renderer)
    plot.renderers.append(graph_renderer)


def prepare_bokeh_render(graph: nx.DiGraph, layout: str) -> PreparedBokehRender:
    """Prepare layout and visual attributes for Bokeh rendering."""
    node_visual_data = _build_node_visual_data(graph)
    final_positions, folder_rect_data = _build_bokeh_layout(graph, layout, node_visual_data)

    return PreparedBokehRender(
        final_positions=final_positions,
        folder_rect_data=folder_rect_data,
        arrow_source_data=_build_arrow_source_data(graph, final_positions),
        node_visual_data=node_visual_data,
    )


def draw_bokeh_graph(graph: nx.DiGraph, layout: str) -> str | None:
    """Render a dependency graph with Bokeh."""
    render_data = prepare_bokeh_render(graph, layout)
    graph_to_draw = _copy_graph_with_visual_data(graph, render_data.node_visual_data)
    edge_style = _build_edge_visual_style(graph)
    render_policy = _build_render_policy(graph)
    plot = _build_plot_for_render(render_data, render_policy)
    _render_graph_on_plot(
        graph_to_draw,
        render_data,
        edge_style,
        plot,
        show_arrows=render_policy.show_arrows,
    )

    return _present_plot(plot)
