"""Bokeh-based graph rendering."""

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


FREEZE_RANDOM_SEED: Final[int] = 42
LABEL_PADDING: Final[float] = 20.0
MIN_NODE_SIZE: Final[int] = 20
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

    for node_id, data in graph.nodes(data=True):
        node_name = str(node_id)
        folder_name = str(data.get("folder", ""))
        if bool(data.get("is_root_folder", False)):
            root_folder_nodes.append(node_name)
            continue

        folder_to_nodes[folder_name].append(node_name)

    return dict(folder_to_nodes), root_folder_nodes


def _build_folder_graph(folder_to_nodes: Mapping[str, Sequence[str]]) -> nx.Graph:
    folder_graph = nx.Graph()
    all_folders = set(folder_to_nodes)

    for folder_name in all_folders:
        folder_graph.add_node(folder_name, label=folder_name.split("/")[-1])
        parent_folder = "/".join(folder_name.split("/")[:-1])
        if parent_folder in all_folders:
            folder_graph.add_edge(parent_folder, folder_name)

    return folder_graph


def _build_folder_positions(
    folder_graph: nx.Graph,
    folder_layout_k: float,
) -> dict[str, tuple[float, float]]:
    return _normalize_layout_positions(
        cast(
            "Mapping[str, Sequence[float]]",
            nx.spring_layout(
                folder_graph,
                k=folder_layout_k,
                iterations=100,
                seed=FREEZE_RANDOM_SEED,
                scale=20,
            ),
        )
    )


def _place_nodes_within_folders(
    graph: nx.DiGraph,
    folder_to_nodes: Mapping[str, Sequence[str]],
    folder_positions: Mapping[str, tuple[float, float]],
    node_layout_k: float,
) -> dict[str, tuple[float, float]]:
    final_positions: dict[str, tuple[float, float]] = {}

    for folder_name, nodes_in_folder in folder_to_nodes.items():
        subgraph = graph.subgraph(nodes_in_folder)
        local_positions = _normalize_layout_positions(
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
        folder_center_x, folder_center_y = folder_positions[folder_name]
        for node_id, (x_coord, y_coord) in local_positions.items():
            final_positions[node_id] = (x_coord + folder_center_x, y_coord + folder_center_y)

    return final_positions


def _get_folder_and_child_nodes(
    folder_name: str,
    folder_to_nodes: Mapping[str, Sequence[str]],
    sorted_folders: Sequence[str],
) -> list[str]:
    all_child_nodes = list(folder_to_nodes[folder_name])
    for other_folder in sorted_folders:
        if other_folder.startswith(folder_name + "/"):
            all_child_nodes.extend(folder_to_nodes[other_folder])

    return all_child_nodes


def _build_folder_rect_data(
    folder_to_nodes: Mapping[str, Sequence[str]],
    final_positions: Mapping[str, tuple[float, float]],
    *,
    padding: float = 1.0,
) -> FolderRectData:
    folder_rect_data: FolderRectData = {
        "x": [],
        "y": [],
        "width": [],
        "height": [],
        "name": [],
        "color": [],
    }
    sorted_folders = sorted(
        folder_to_nodes.keys(),
        key=lambda folder_name: folder_name.count("/"),
        reverse=True,
    )

    for folder_name in sorted_folders:
        all_child_nodes = _get_folder_and_child_nodes(folder_name, folder_to_nodes, sorted_folders)
        coords = [
            final_positions[node_id]
            for node_id in all_child_nodes
            if node_id in final_positions
        ]
        if not coords:
            continue

        min_x = min(x_coord for x_coord, _ in coords) - padding
        max_x = max(x_coord for x_coord, _ in coords) + padding
        min_y = min(y_coord for _, y_coord in coords) - padding
        max_y = max(y_coord for _, y_coord in coords) + padding

        folder_rect_data["x"].append((min_x + max_x) / 2)
        folder_rect_data["y"].append((min_y + max_y) / 2)
        folder_rect_data["width"].append(max_x - min_x)
        folder_rect_data["height"].append(max_y - min_y)
        folder_rect_data["name"].append(folder_name.split("/")[-1])
        folder_rect_data["color"].append("#E8E8E8")

    return folder_rect_data


def _add_root_folder_positions(
    graph: nx.DiGraph,
    root_folder_nodes: Sequence[str],
    final_positions: dict[str, tuple[float, float]],
    node_layout_k: float,
) -> None:
    if not root_folder_nodes:
        return

    root_subgraph = graph.subgraph(root_folder_nodes)
    root_positions = _normalize_layout_positions(
        cast(
            "Mapping[str, Sequence[float]]",
            nx.spring_layout(
                root_subgraph,
                k=node_layout_k,
                iterations=50,
                seed=FREEZE_RANDOM_SEED,
                scale=5,
                center=(0, 0),
            ),
        )
    )
    final_positions.update(root_positions)


def _create_constrained_layout(
    graph: nx.DiGraph,
    *,
    folder_layout_k: float = 2,
    node_layout_k: float = 0.5,
) -> tuple[dict[str, tuple[float, float]], FolderRectData]:
    folder_to_nodes, root_folder_nodes = _collect_folder_nodes(graph)
    folder_graph = _build_folder_graph(folder_to_nodes)
    folder_positions = _build_folder_positions(folder_graph, folder_layout_k)
    final_positions = _place_nodes_within_folders(
        graph,
        folder_to_nodes,
        folder_positions,
        node_layout_k,
    )
    folder_rect_data = _build_folder_rect_data(folder_to_nodes, final_positions)
    _add_root_folder_positions(graph, root_folder_nodes, final_positions, node_layout_k)

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

    for node_id in list(graph.nodes()):
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
    for node_id, node_data in graph.nodes(data=True):
        graph_to_draw.add_node(node_id, **dict(node_data))
    for start_node, end_node in graph.edges():
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
        y="y",
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

    for start_node, end_node in graph.edges():
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
