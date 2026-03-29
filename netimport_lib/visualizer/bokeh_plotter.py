"""Bokeh-based graph rendering."""

import math
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, TypedDict, cast

import networkx as nx
from bokeh.io import save
from bokeh.models.annotations.arrows import Arrow, OpenHead
from bokeh.models.annotations.labels import LabelSet
from bokeh.models.glyphs import MultiLine, Scatter
from bokeh.models.graphs import NodesAndLinkedEdges
from bokeh.models.renderers import GraphRenderer
from bokeh.models.sources import ColumnDataSource
from bokeh.models.tools import (
    BoxZoomTool,
    HoverTool,
    PanTool,
    PointDrawTool,
    ResetTool,
    SaveTool,
    TapTool,
    WheelZoomTool,
)
from bokeh.plotting import from_networkx
from bokeh.plotting._figure import figure as figure_model
from bokeh.resources import CDN
from bokeh.util.browser import get_browser_controller


class FolderRectData(TypedDict):
    """Rectangular overlay data for folder groups."""

    x: list[float]
    y: list[float]
    label_y: list[float]
    width: list[float]
    height: list[float]
    name: list[str]
    color: list[str]


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


@dataclass(frozen=True, slots=True)
class PreparedBokehRender:
    """Data prepared for Bokeh rendering."""

    final_positions: dict[str, tuple[float, float]]
    folder_rect_data: FolderRectData
    arrow_source_data: ArrowSourceData
    node_visual_data: dict[object, NodeVisualData]


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
    node_positions: dict[str, tuple[float, float]]
    child_origins: dict[str, tuple[float, float]]


FREEZE_RANDOM_SEED: Final[int] = 42
LABEL_PADDING: Final[float] = 20.0
MIN_NODE_SIZE: Final[int] = 20
MIN_NODE_BLOCK_SPAN: Final[float] = 4.0
NODE_BLOCK_CELL_SPAN: Final[float] = 4.0
NODE_LAYOUT_INSET: Final[float] = 0.75
FOLDER_PADDING_X: Final[float] = 1.5
FOLDER_PADDING_Y: Final[float] = 1.5
FOLDER_LABEL_HEIGHT: Final[float] = 1.75
FOLDER_SECTION_GAP: Final[float] = 1.5
FOLDER_GRID_GAP_X: Final[float] = 2.0
FOLDER_GRID_GAP_Y: Final[float] = 2.0
ROOT_SECTION_GAP: Final[float] = 3.0
MIN_FOLDER_CONTENT_WIDTH: Final[float] = 4.0
MIN_FOLDER_CONTENT_HEIGHT: Final[float] = 3.0
COLOR_MAP: Final[Mapping[str, str]] = MappingProxyType(
    {
        "project_file": "skyblue",
        "std_lib": "lightgreen",
        "external_lib": "salmon",
        "unresolved": "lightgray",
        "unresolved_relative": "silver",
        "unresolved_relative_internal_error": "silver",
        "unresolved_relative_too_many_dots": "silver",
    }
)
DEFAULT_NODE_COLOR: Final[str] = "red"
BOKEH_OUTPUT_PREFIX: Final[str] = "netimport-"
BOKEH_OUTPUT_SUFFIX: Final[str] = ".html"
BOKEH_PLOT_TITLE: Final[str] = "NetImport dependency graph"
SKIPPED_AUTO_OPEN_CONTROLLER_NAMES: Final[frozenset[str]] = frozenset({"MacOSXOSAScript"})


def _normalize_layout_positions(
    raw_positions: Mapping[str, Sequence[float]],
) -> dict[str, tuple[float, float]]:
    return {
        node_id: (float(position[0]), float(position[1]))
        for node_id, position in raw_positions.items()
    }


def _collect_folder_nodes(graph: nx.DiGraph) -> tuple[dict[str, list[str]], list[str]]:
    folder_to_nodes: defaultdict[str, list[str]] = defaultdict(list)
    root_folder_nodes: list[str] = []

    ordered_nodes = sorted(graph.nodes(data=True), key=lambda item: str(item[0]))
    for node_id, data in ordered_nodes:
        node_name = str(node_id)
        folder_name = str(data.get("folder", ""))
        if bool(data.get("is_root_folder", False)):
            root_folder_nodes.append(node_name)
            continue

        folder_to_nodes[folder_name].append(node_name)

    return dict(folder_to_nodes), root_folder_nodes


def _build_folder_hierarchy(
    folder_to_nodes: Mapping[str, Sequence[str]],
) -> tuple[list[str], dict[str, list[str]]]:
    all_folders = tuple(sorted(folder_to_nodes))
    folder_set = set(all_folders)
    root_folders: list[str] = []
    child_folders: dict[str, list[str]] = {folder_name: [] for folder_name in all_folders}

    for folder_name in all_folders:
        parent_folder = "/".join(folder_name.split("/")[:-1])
        if parent_folder in folder_set:
            child_folders[parent_folder].append(folder_name)
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
    candidate_edges = sorted(
        graph.subgraph(ordered_nodes).edges(),
        key=lambda edge: (str(edge[0]), str(edge[1])),
    )
    for start_node, end_node in candidate_edges:
        subgraph.add_edge(start_node, end_node)
    return subgraph


def _scale_positions_to_block(
    raw_positions: Mapping[str, tuple[float, float]],
    *,
    width: float,
    height: float,
    inset: float,
) -> dict[str, tuple[float, float]]:
    if not raw_positions:
        return {}

    x_values = [x_coord for x_coord, _ in raw_positions.values()]
    y_values = [y_coord for _, y_coord in raw_positions.values()]
    min_x = min(x_values)
    max_x = max(x_values)
    min_y = min(y_values)
    max_y = max(y_values)
    usable_width = max(width - 2 * inset, 0.0)
    usable_height = max(height - 2 * inset, 0.0)
    center_x = width / 2.0
    center_y = height / 2.0
    scaled_positions: dict[str, tuple[float, float]] = {}

    for node_id in sorted(raw_positions):
        raw_x, raw_y = raw_positions[node_id]
        if max_x == min_x:
            scaled_x = center_x
        else:
            scaled_x = inset + ((raw_x - min_x) / (max_x - min_x)) * usable_width
        if max_y == min_y:
            scaled_y = center_y
        else:
            scaled_y = inset + ((raw_y - min_y) / (max_y - min_y)) * usable_height
        scaled_positions[node_id] = (scaled_x, scaled_y)

    return scaled_positions


def _build_local_node_layout(
    graph: nx.DiGraph,
    node_ids: Sequence[str],
    node_layout_k: float,
) -> LocalNodeLayout:
    ordered_nodes = tuple(sorted(node_ids))
    if not ordered_nodes:
        return LocalNodeLayout(width=0.0, height=0.0, positions={})

    if len(ordered_nodes) == 1:
        width = MIN_NODE_BLOCK_SPAN
        height = MIN_NODE_BLOCK_SPAN
        return LocalNodeLayout(
            width=width,
            height=height,
            positions={ordered_nodes[0]: (width / 2.0, height / 2.0)},
        )

    column_count = max(1, math.ceil(math.sqrt(len(ordered_nodes))))
    row_count = math.ceil(len(ordered_nodes) / column_count)
    width = max(MIN_NODE_BLOCK_SPAN, float(column_count) * NODE_BLOCK_CELL_SPAN)
    height = max(MIN_NODE_BLOCK_SPAN, float(row_count) * NODE_BLOCK_CELL_SPAN)
    subgraph = _build_sorted_layout_subgraph(graph, ordered_nodes)
    raw_positions = _normalize_layout_positions(
        cast(
            "Mapping[str, Sequence[float]]",
            nx.spring_layout(
                subgraph,
                k=node_layout_k,
                iterations=50,
                seed=FREEZE_RANDOM_SEED,
                scale=1,
            ),
        )
    )
    return LocalNodeLayout(
        width=width,
        height=height,
        positions=_scale_positions_to_block(
            raw_positions,
            width=width,
            height=height,
            inset=NODE_LAYOUT_INSET,
        ),
    )


def _pack_boxes(
    item_sizes: Sequence[tuple[str, float, float]],
    *,
    gap_x: float,
    gap_y: float,
) -> PackedBoxLayout:
    ordered_items = tuple(sorted(item_sizes, key=lambda item: item[0]))
    if not ordered_items:
        return PackedBoxLayout(width=0.0, height=0.0, origins={})

    if len(ordered_items) == 1:
        item_name, item_width, item_height = ordered_items[0]
        return PackedBoxLayout(
            width=item_width,
            height=item_height,
            origins={item_name: (0.0, 0.0)},
        )

    column_count = max(1, math.ceil(math.sqrt(len(ordered_items))))
    row_count = math.ceil(len(ordered_items) / column_count)
    column_widths = [0.0] * column_count
    row_heights = [0.0] * row_count

    for index, (_item_name, item_width, item_height) in enumerate(ordered_items):
        row_index = index // column_count
        column_index = index % column_count
        column_widths[column_index] = max(column_widths[column_index], item_width)
        row_heights[row_index] = max(row_heights[row_index], item_height)

    total_width = sum(column_widths) + gap_x * max(column_count - 1, 0)
    total_height = sum(row_heights) + gap_y * max(row_count - 1, 0)
    x_offsets: list[float] = []
    current_x = 0.0
    for column_width in column_widths:
        x_offsets.append(current_x)
        current_x += column_width + gap_x

    row_bottoms: list[float] = []
    current_y_top = total_height
    for row_height in row_heights:
        row_bottom = current_y_top - row_height
        row_bottoms.append(row_bottom)
        current_y_top = row_bottom - gap_y

    origins: dict[str, tuple[float, float]] = {}
    for index, (item_name, item_width, item_height) in enumerate(ordered_items):
        row_index = index // column_count
        column_index = index % column_count
        origin_x = x_offsets[column_index] + (column_widths[column_index] - item_width) / 2.0
        origin_y = row_bottoms[row_index] + (row_heights[row_index] - item_height) / 2.0
        origins[item_name] = (origin_x, origin_y)

    return PackedBoxLayout(width=total_width, height=total_height, origins=origins)


def _build_folder_container_layout(  # noqa: PLR0913
    graph: nx.DiGraph,
    folder_name: str,
    folder_to_nodes: Mapping[str, Sequence[str]],
    child_folders: Mapping[str, Sequence[str]],
    node_layout_k: float,
    folder_layouts: dict[str, ContainerLayout],
) -> ContainerLayout:
    direct_nodes_layout = _build_local_node_layout(
        graph,
        folder_to_nodes.get(folder_name, ()),
        node_layout_k,
    )
    child_names = tuple(sorted(child_folders.get(folder_name, ())))
    child_box_sizes = [
        (child_name, folder_layouts[child_name].width, folder_layouts[child_name].height)
        for child_name in child_names
    ]
    packed_children = _pack_boxes(
        child_box_sizes,
        gap_x=FOLDER_GRID_GAP_X,
        gap_y=FOLDER_GRID_GAP_Y,
    )
    content_width = max(
        MIN_FOLDER_CONTENT_WIDTH,
        direct_nodes_layout.width,
        packed_children.width,
    )
    sections_height = packed_children.height + direct_nodes_layout.height
    if packed_children.height > 0.0 and direct_nodes_layout.height > 0.0:
        sections_height += FOLDER_SECTION_GAP
    content_height = max(MIN_FOLDER_CONTENT_HEIGHT, sections_height)
    child_origin_x = FOLDER_PADDING_X + (content_width - packed_children.width) / 2.0
    child_origin_y = FOLDER_PADDING_Y
    direct_origin_x = FOLDER_PADDING_X + (content_width - direct_nodes_layout.width) / 2.0
    has_child_section = packed_children.height > 0.0
    has_direct_node_section = direct_nodes_layout.height > 0.0
    section_gap = (
        FOLDER_SECTION_GAP if has_child_section and has_direct_node_section else 0.0
    )
    direct_origin_y = (
        FOLDER_PADDING_Y
        + packed_children.height
        + section_gap
    )
    node_positions = {
        node_id: (direct_origin_x + local_x, direct_origin_y + local_y)
        for node_id, (local_x, local_y) in direct_nodes_layout.positions.items()
    }
    child_origins = {
        child_name: (child_origin_x + local_x, child_origin_y + local_y)
        for child_name, (local_x, local_y) in packed_children.origins.items()
    }

    return ContainerLayout(
        width=content_width + 2 * FOLDER_PADDING_X,
        height=content_height + 2 * FOLDER_PADDING_Y + FOLDER_LABEL_HEIGHT,
        node_positions=node_positions,
        child_origins=child_origins,
    )


def _build_root_container_layout(
    graph: nx.DiGraph,
    root_folder_nodes: Sequence[str],
    root_folders: Sequence[str],
    folder_layouts: Mapping[str, ContainerLayout],
    node_layout_k: float,
) -> ContainerLayout:
    root_nodes_layout = _build_local_node_layout(graph, root_folder_nodes, node_layout_k)
    root_child_sizes = [
        (folder_name, folder_layouts[folder_name].width, folder_layouts[folder_name].height)
        for folder_name in sorted(root_folders)
    ]
    packed_root_folders = _pack_boxes(
        root_child_sizes,
        gap_x=FOLDER_GRID_GAP_X,
        gap_y=FOLDER_GRID_GAP_Y,
    )
    total_width = max(root_nodes_layout.width, packed_root_folders.width)
    total_height = packed_root_folders.height + root_nodes_layout.height
    has_root_folder_section = packed_root_folders.height > 0.0
    has_root_node_section = root_nodes_layout.height > 0.0
    root_section_gap = (
        ROOT_SECTION_GAP if has_root_folder_section and has_root_node_section else 0.0
    )
    total_height += root_section_gap

    folder_origin_x = (total_width - packed_root_folders.width) / 2.0
    folder_origin_y = 0.0
    node_origin_x = (total_width - root_nodes_layout.width) / 2.0
    node_origin_y = packed_root_folders.height + root_section_gap
    node_positions = {
        node_id: (node_origin_x + local_x, node_origin_y + local_y)
        for node_id, (local_x, local_y) in root_nodes_layout.positions.items()
    }
    child_origins = {
        folder_name: (folder_origin_x + local_x, folder_origin_y + local_y)
        for folder_name, (local_x, local_y) in packed_root_folders.origins.items()
    }

    return ContainerLayout(
        width=total_width,
        height=total_height,
        node_positions=node_positions,
        child_origins=child_origins,
    )


def _build_folder_rect_data() -> FolderRectData:
    return {
        "x": [],
        "y": [],
        "label_y": [],
        "width": [],
        "height": [],
        "name": [],
        "color": [],
    }


def _append_folder_rect(
    folder_rect_data: FolderRectData,
    folder_name: str,
    origin_x: float,
    origin_y: float,
    layout: ContainerLayout,
) -> None:
    folder_rect_data["x"].append(origin_x + layout.width / 2.0)
    folder_rect_data["y"].append(origin_y + layout.height / 2.0)
    folder_rect_data["label_y"].append(
        origin_y + layout.height - FOLDER_PADDING_Y - FOLDER_LABEL_HEIGHT / 2.0
    )
    folder_rect_data["width"].append(layout.width)
    folder_rect_data["height"].append(layout.height)
    folder_rect_data["name"].append(folder_name.rsplit("/", maxsplit=1)[-1])
    folder_rect_data["color"].append("#E8E8E8")


def _assign_folder_positions(  # noqa: PLR0913
    folder_name: str,
    origin_x: float,
    origin_y: float,
    folder_layouts: Mapping[str, ContainerLayout],
    folder_rect_data: FolderRectData,
    final_positions: dict[str, tuple[float, float]],
) -> None:
    layout = folder_layouts[folder_name]
    _append_folder_rect(folder_rect_data, folder_name, origin_x, origin_y, layout)

    for node_id in sorted(layout.node_positions):
        relative_x, relative_y = layout.node_positions[node_id]
        final_positions[node_id] = (origin_x + relative_x, origin_y + relative_y)

    for child_name in sorted(layout.child_origins):
        child_origin_x, child_origin_y = layout.child_origins[child_name]
        _assign_folder_positions(
            child_name,
            origin_x + child_origin_x,
            origin_y + child_origin_y,
            folder_layouts,
            folder_rect_data,
            final_positions,
        )


def _create_constrained_layout(
    graph: nx.DiGraph,
    *,
    node_layout_k: float = 0.5,
) -> tuple[dict[str, tuple[float, float]], FolderRectData]:
    folder_to_nodes, root_folder_nodes = _collect_folder_nodes(graph)
    root_folders, child_folders = _build_folder_hierarchy(folder_to_nodes)
    folder_layouts: dict[str, ContainerLayout] = {}

    for folder_name in sorted(
        folder_to_nodes,
        key=lambda name: (name.count("/"), name),
        reverse=True,
    ):
        folder_layouts[folder_name] = _build_folder_container_layout(
            graph,
            folder_name,
            folder_to_nodes,
            child_folders,
            node_layout_k,
            folder_layouts,
        )

    root_layout = _build_root_container_layout(
        graph,
        root_folder_nodes,
        root_folders,
        folder_layouts,
        node_layout_k,
    )
    final_positions = {
        node_id: (
            relative_x - root_layout.width / 2.0,
            relative_y - root_layout.height / 2.0,
        )
        for node_id, (relative_x, relative_y) in root_layout.node_positions.items()
    }
    folder_rect_data = _build_folder_rect_data()
    root_origin_x = -root_layout.width / 2.0
    root_origin_y = -root_layout.height / 2.0
    for folder_name in sorted(root_layout.child_origins):
        child_origin_x, child_origin_y = root_layout.child_origins[folder_name]
        _assign_folder_positions(
            folder_name,
            root_origin_x + child_origin_x,
            root_origin_y + child_origin_y,
            folder_layouts,
            folder_rect_data,
            final_positions,
        )
    return final_positions, folder_rect_data


def _build_bokeh_layout(
    graph: nx.DiGraph,
    layout: str,
) -> tuple[dict[str, tuple[float, float]], FolderRectData]:
    if layout != "constrained":
        raise ValueError(f"Unsupported Bokeh layout '{layout}'. Supported layouts: constrained.")

    return _create_constrained_layout(graph)


def _build_node_visual_data(graph: nx.DiGraph) -> dict[object, NodeVisualData]:
    degrees = dict(graph.degree())
    visual_data: dict[object, NodeVisualData] = {}

    for node_id in sorted(graph.nodes(), key=str):
        node_data = graph.nodes[node_id]
        current_degree = degrees.get(node_id, 0)
        calculated_size = MIN_NODE_SIZE + current_degree * 10

        visual_data[node_id] = {
            "viz_size": calculated_size,
            "viz_color": COLOR_MAP.get(
                str(node_data.get("type", "unresolved")),
                DEFAULT_NODE_COLOR,
            ),
            "viz_label": str(node_data.get("label", node_id)),
            "viz_degree": current_degree,
            "viz_type": str(node_data.get("type", "unresolved")),
            "viz_label_y_offset": int(calculated_size / 2.0 + LABEL_PADDING),
            "in_degree": _to_int(node_data.get("in_degree", 0)),
            "out_degree": _to_int(node_data.get("out_degree", 0)),
            "total_degree": _to_int(node_data.get("total_degree", 0)),
        }

    return visual_data


def _copy_graph_with_visual_data(
    graph: nx.DiGraph,
    node_visual_data: Mapping[object, NodeVisualData],
) -> nx.DiGraph:
    graph_to_draw = nx.DiGraph()
    for node_id, node_data in sorted(graph.nodes(data=True), key=lambda item: str(item[0])):
        graph_to_draw.add_node(node_id, **dict(node_data))
    sorted_edges = sorted(
        graph.edges(),
        key=lambda edge: (str(edge[0]), str(edge[1])),
    )
    for start_node, end_node in sorted_edges:
        graph_to_draw.add_edge(start_node, end_node)
    for node_id, visual_data in node_visual_data.items():
        graph_to_draw.nodes[node_id].update(visual_data)

    return graph_to_draw


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return 0


def _create_bokeh_plot(folder_rect_data: FolderRectData) -> tuple[figure_model, ColumnDataSource]:
    plot = figure_model(title="Interactive dependency graph")
    plot.sizing_mode = "scale_both"
    plot.output_backend = "webgl"

    pan_tool = PanTool()
    hover_tool = HoverTool()
    plot.add_tools(
        pan_tool,
        WheelZoomTool(),
        BoxZoomTool(),
        ResetTool(),
        SaveTool(),
        TapTool(),
        hover_tool,
    )
    plot.toolbar.active_drag = pan_tool
    plot.toolbar.active_inspect = hover_tool

    folder_source = ColumnDataSource(data=folder_rect_data)
    plot.rect(
        x="x",
        y="y",
        width="width",
        height="height",
        source=folder_source,
        fill_color="color",
        fill_alpha=0.4,
        line_color="black",
        line_dash="dashed",
        level="underlay",
    )

    folder_labels = LabelSet(
        x="x",
        y="label_y",
        text="name",
        source=folder_source,
        text_font_size="12pt",
        text_color="black",
        text_align="center",
        y_offset=0,
        level="overlay",
    )
    plot.add_layout(folder_labels)

    return plot, folder_source


def _sync_node_coordinates(
    graph_renderer: GraphRenderer,
    final_positions: Mapping[str, tuple[float, float]],
) -> None:
    data_source = cast("ColumnDataSource", graph_renderer.node_renderer.data_source)
    node_data = data_source.data
    indices = node_data.get("index")
    if not isinstance(indices, list) or not indices:
        return
    if isinstance(node_data.get("x"), list) and isinstance(node_data.get("y"), list):
        return

    ordered_node_ids = [str(node_id) for node_id in indices]
    try:
        node_xs = [final_positions[node_id][0] for node_id in ordered_node_ids]
        node_ys = [final_positions[node_id][1] for node_id in ordered_node_ids]
    except KeyError:
        return

    node_data["x"] = node_xs
    node_data["y"] = node_ys


def _configure_node_renderer(graph_renderer: GraphRenderer) -> None:
    graph_renderer.node_renderer.glyph = Scatter(
        marker="circle",
        size="viz_size",
        fill_color="viz_color",
        fill_alpha=0.8,
        line_color="black",
        line_width=0.5,
    )
    graph_renderer.node_renderer.hover_glyph = Scatter(
        marker="circle",
        size="viz_size",
        fill_color="orange",
        fill_alpha=0.8,
        line_color="black",
        line_width=2,
    )
    graph_renderer.node_renderer.selection_glyph = Scatter(
        marker="circle",
        size="viz_size",
        fill_color="firebrick",
        fill_alpha=0.8,
        line_color="black",
        line_width=2,
    )


def _configure_edge_renderer(graph_renderer: GraphRenderer) -> None:
    graph_renderer.edge_renderer.glyph = MultiLine(
        line_color="#CCCCCC",
        line_alpha=0.8,
        line_width=1.5,
    )
    graph_renderer.edge_renderer.hover_glyph = MultiLine(line_color="orange", line_width=2)
    graph_renderer.edge_renderer.selection_glyph = MultiLine(line_color="firebrick", line_width=2)


def _build_arrow_source_data(
    graph: nx.DiGraph,
    final_positions: Mapping[str, tuple[float, float]],
) -> ArrowSourceData:
    arrow_source_data: ArrowSourceData = {
        "start_x": [],
        "start_y": [],
        "end_x": [],
        "end_y": [],
    }

    sorted_edges = sorted(
        graph.edges(),
        key=lambda edge: (str(edge[0]), str(edge[1])),
    )
    for start_node, end_node in sorted_edges:
        start_coords = final_positions[str(start_node)]
        end_coords = final_positions[str(end_node)]
        arrow_source_data["start_x"].append(start_coords[0])
        arrow_source_data["start_y"].append(start_coords[1])
        arrow_source_data["end_x"].append(end_coords[0])
        arrow_source_data["end_y"].append(end_coords[1])

    return arrow_source_data


def _add_arrow_renderer(
    plot: figure_model,
    arrow_source_data: ArrowSourceData,
) -> None:
    arrow_source = ColumnDataSource(data=arrow_source_data)
    arrow_renderer = Arrow(
        end=OpenHead(line_color="gray", line_width=2, size=12),
        source=arrow_source,
        x_start="start_x",
        y_start="start_y",
        x_end="end_x",
        y_end="end_y",
    )
    plot.add_layout(arrow_renderer)


def _configure_hover(plot: figure_model, graph_renderer: GraphRenderer) -> None:
    hover_tool = cast("HoverTool | None", plot.select_one({"type": HoverTool}))
    if hover_tool is None:
        return

    hover_tool.renderers = [graph_renderer.node_renderer]
    hover_tool.tooltips = [
        ("Name", "@viz_label"),
        ("Type", "@viz_type"),
        ("Total Links", "@total_degree"),
        ("Incoming", "@in_degree"),
        ("Outgoing", "@out_degree"),
        ("ID", "@index"),
        ("Folder", "@folder"),
    ]


def _enable_node_dragging(plot: figure_model, graph_renderer: GraphRenderer) -> None:
    point_draw_tool = PointDrawTool(renderers=[graph_renderer.node_renderer])
    plot.add_tools(point_draw_tool)
    plot.toolbar.active_drag = point_draw_tool


def _build_bokeh_output_path() -> Path:
    with tempfile.NamedTemporaryFile(
        prefix=BOKEH_OUTPUT_PREFIX,
        suffix=BOKEH_OUTPUT_SUFFIX,
        delete=False,
    ) as file_handle:
        return Path(file_handle.name)


def _save_plot(plot: figure_model) -> Path:
    output_path = _build_bokeh_output_path()
    save(plot, filename=output_path, resources=CDN, title=BOKEH_PLOT_TITLE)
    return output_path


def _run_open_command(command: Sequence[str]) -> bool:
    try:
        completed_process = subprocess.run(  # noqa: S603
            command,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False

    return completed_process.returncode == 0


def _open_with_platform_command(output_path: Path) -> bool:
    if sys.platform == "darwin":
        return _run_open_command(("open", str(output_path)))

    if sys.platform.startswith("linux"):
        opener = shutil.which("xdg-open")
        if opener is None:
            return False
        return _run_open_command((opener, str(output_path)))

    if os.name == "nt":
        try:
            os.startfile(str(output_path))  # noqa: S606
        except OSError:
            return False
        return True

    return False


def _should_skip_auto_open(controller: object) -> bool:
    if controller is webbrowser and sys.platform == "darwin":
        return True
    return controller.__class__.__name__ in SKIPPED_AUTO_OPEN_CONTROLLER_NAMES


def _open_saved_plot(output_path: Path) -> bool:
    if _open_with_platform_command(output_path):
        return True

    try:
        controller = get_browser_controller(browser=None)
        if _should_skip_auto_open(controller):
            return False
        return bool(controller.open(output_path.as_uri(), new=2, autoraise=True))
    except (OSError, webbrowser.Error):
        return False


def _build_manual_open_message(output_path: Path) -> str:
    return (
        "Interactive dependency graph saved to "
        f"{output_path}. Automatic browser launch is unavailable in this environment; "
        "open the file manually."
    )


def _present_plot(plot: figure_model) -> str | None:
    output_path = _save_plot(plot)
    if _open_saved_plot(output_path):
        return None
    return _build_manual_open_message(output_path)


def prepare_bokeh_render(graph: nx.DiGraph, layout: str) -> PreparedBokehRender:
    """Prepare layout and visual attributes for Bokeh rendering."""
    final_positions, folder_rect_data = _build_bokeh_layout(graph, layout)

    return PreparedBokehRender(
        final_positions=final_positions,
        folder_rect_data=folder_rect_data,
        arrow_source_data=_build_arrow_source_data(graph, final_positions),
        node_visual_data=_build_node_visual_data(graph),
    )


def draw_bokeh_graph(graph: nx.DiGraph, layout: str) -> str | None:
    """Render a dependency graph with Bokeh."""
    render_data = prepare_bokeh_render(graph, layout)
    graph_to_draw = _copy_graph_with_visual_data(graph, render_data.node_visual_data)
    plot, _folder_source = _create_bokeh_plot(render_data.folder_rect_data)
    graph_renderer = from_networkx(
        graph_to_draw,
        cast("dict[int | str, Sequence[float]]", render_data.final_positions),
    )
    _sync_node_coordinates(graph_renderer, render_data.final_positions)
    _configure_node_renderer(graph_renderer)
    _configure_edge_renderer(graph_renderer)
    _add_arrow_renderer(plot, render_data.arrow_source_data)
    graph_renderer.selection_policy = NodesAndLinkedEdges()
    graph_renderer.inspection_policy = NodesAndLinkedEdges()
    _configure_hover(plot, graph_renderer)
    _enable_node_dragging(plot, graph_renderer)
    plot.renderers.append(graph_renderer)

    return _present_plot(plot)
