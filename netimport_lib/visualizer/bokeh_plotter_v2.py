from collections import defaultdict
from typing import Any

import networkx as nx
from bokeh.models import (
    Arrow,
    Circle,
    ColumnDataSource,
    HoverTool,
    LabelSet,
    MultiLine,
    NodesAndLinkedEdges,
    OpenHead,
)
from bokeh.plotting import figure, from_networkx, show


FREEZ_RANDOM_SEED = 42
COLOR_MAP = {
    "project_file": "skyblue",
    "std_lib": "lightgreen",
    "external_lib": "salmon",
    "unresolved": "lightgray",
    "unresolved_relative": "silver",
}
DEFAULT_NODE_COLOR = "red"
MIN_NODE_SIZE_CONSTANT = 20
LABEL_PADDING = 20


def _collect_folder_nodes(graph: nx.DiGraph) -> tuple[defaultdict[str, list], list]:
    folder_to_nodes: defaultdict[str, list] = defaultdict(list)
    root_folder_nodes = []

    for node, data in graph.nodes(data=True):
        if data.get("is_root_folder"):
            root_folder_nodes.append(node)
            continue

        folder_to_nodes[data["folder"]].append(node)

    return folder_to_nodes, root_folder_nodes


def _build_folder_graph(folder_to_nodes: defaultdict[str, list]) -> nx.Graph:
    folder_graph = nx.Graph()
    all_folders = list(folder_to_nodes.keys())

    for folder in all_folders:
        folder_graph.add_node(folder, label=folder.split("/")[-1])
        parent_folder = "/".join(folder.split("/")[:-1])
        if parent_folder in all_folders:
            folder_graph.add_edge(parent_folder, folder)

    return folder_graph


def _build_folder_positions(folder_graph: nx.Graph, folder_layout_k: float) -> dict:
    return nx.spring_layout(
        folder_graph,
        k=folder_layout_k,
        iterations=100,
        seed=FREEZ_RANDOM_SEED,
        scale=20,
    )


def _place_nodes_within_folders(
    graph: nx.DiGraph,
    folder_to_nodes: defaultdict[str, list],
    folder_pos: dict,
    node_layout_k: float,
) -> dict:
    final_pos = {}

    for folder_name, nodes_in_folder in folder_to_nodes.items():
        subgraph = graph.subgraph(nodes_in_folder)
        local_pos = nx.spring_layout(
            subgraph,
            k=node_layout_k,
            iterations=50,
            seed=FREEZ_RANDOM_SEED,
            scale=1,
        )

        folder_center_x, folder_center_y = folder_pos[folder_name]
        for node, (x, y) in local_pos.items():
            final_pos[node] = (x + folder_center_x, y + folder_center_y)

    return final_pos


def _get_folder_and_child_nodes(
    folder_name: str,
    folder_to_nodes: defaultdict[str, list],
    sorted_folders: list[str],
) -> list:
    all_child_nodes = list(folder_to_nodes[folder_name])

    for other_folder in sorted_folders:
        if other_folder.startswith(folder_name + "/"):
            all_child_nodes.extend(folder_to_nodes[other_folder])

    return all_child_nodes


def _build_folder_rect_data(
    folder_to_nodes: defaultdict[str, list],
    final_pos: dict,
    padding: float = 1.0,
) -> defaultdict[str, list]:
    folder_rect_data: defaultdict[str, list] = defaultdict(list)
    sorted_folders = sorted(folder_to_nodes.keys(), key=lambda folder_name: folder_name.count("/"), reverse=True)

    for folder_name in sorted_folders:
        all_child_nodes = _get_folder_and_child_nodes(folder_name, folder_to_nodes, sorted_folders)
        coords = [final_pos[node_id] for node_id in all_child_nodes]
        if not coords:
            continue

        min_x = min(c[0] for c in coords) - padding
        max_x = max(c[0] for c in coords) + padding
        min_y = min(c[1] for c in coords) - padding
        max_y = max(c[1] for c in coords) + padding

        folder_rect_data["x"].append((min_x + max_x) / 2)
        folder_rect_data["y"].append((min_y + max_y) / 2)
        folder_rect_data["width"].append(max_x - min_x)
        folder_rect_data["height"].append(max_y - min_y)
        folder_rect_data["name"].append(folder_name.split("/")[-1])
        folder_rect_data["color"].append("#E8E8E8")

    return folder_rect_data


def _add_root_folder_positions(
    graph: nx.DiGraph,
    root_folder_nodes: list,
    final_pos: dict,
    node_layout_k: float,
) -> None:
    if not root_folder_nodes:
        return

    root_subgraph = graph.subgraph(root_folder_nodes)
    root_pos = nx.spring_layout(
        root_subgraph,
        k=node_layout_k,
        iterations=50,
        seed=FREEZ_RANDOM_SEED,
        scale=5,
        center=(0, 0),
    )
    final_pos.update(root_pos)


def create_constrained_layout(
    graph: nx.DiGraph, folder_layout_k: float = 2, node_layout_k: float = 0.5
) -> tuple[dict, dict]:
    folder_to_nodes, root_folder_nodes = _collect_folder_nodes(graph)
    folder_graph = _build_folder_graph(folder_to_nodes)
    folder_pos = _build_folder_positions(folder_graph, folder_layout_k)
    final_pos = _place_nodes_within_folders(graph, folder_to_nodes, folder_pos, node_layout_k)
    folder_rect_data = _build_folder_rect_data(folder_to_nodes, final_pos)
    _add_root_folder_positions(graph, root_folder_nodes, final_pos, node_layout_k)

    return final_pos, folder_rect_data


def _build_bokeh_layout(graph: nx.DiGraph, layout: str) -> tuple[dict, dict]:
    if layout != "constrained":
        raise ValueError(
            "Unsupported Bokeh layout "
            f"'{layout}'. Supported layouts: constrained."
        )

    return create_constrained_layout(graph)


def _populate_node_visual_data(graph: nx.DiGraph) -> None:
    node_ids_list = list(graph.nodes())
    degrees = dict(graph.degree())

    for node_id in node_ids_list:
        node_original_data = graph.nodes[node_id]
        current_degree = degrees.get(node_id, 0)
        calculated_size = MIN_NODE_SIZE_CONSTANT + current_degree * 10
        calculated_radius_screen = calculated_size / 2.0

        graph.nodes[node_id]["viz_size"] = calculated_size
        graph.nodes[node_id]["viz_radius_screen"] = calculated_radius_screen
        graph.nodes[node_id]["viz_color"] = COLOR_MAP.get(
            node_original_data.get("type", "unresolved"),
            DEFAULT_NODE_COLOR,
        )
        graph.nodes[node_id]["viz_label"] = node_original_data.get("label", str(node_id))
        graph.nodes[node_id]["viz_degree"] = current_degree
        graph.nodes[node_id]["viz_type"] = node_original_data.get("type", "unresolved")
        graph.nodes[node_id]["in_degree"] = node_original_data.get("in_degree", 0)
        graph.nodes[node_id]["out_degree"] = node_original_data.get("out_degree", 0)
        graph.nodes[node_id]["total_degree"] = node_original_data.get("total_degree", 0)
        graph.nodes[node_id]["viz_label_y_offset"] = calculated_radius_screen + LABEL_PADDING


def _create_bokeh_plot(folder_rect_data: dict) -> tuple:
    plot = figure(
        title="Interactive graph with draggable nodes",
        sizing_mode="scale_both",
        tools="pan,wheel_zoom,box_zoom,reset,save,tap,hover,point_draw",
        active_drag="pan",
        active_inspect="hover",
        output_backend="webgl",
    )

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
        text_baseline="bottom",
        y_offset=0,
        level="overlay",
    )
    plot.add_layout(folder_labels)

    return plot, folder_source


def _sync_node_coordinates(graph_renderer: Any, final_pos: dict) -> None:
    node_data_source = graph_renderer.node_renderer.data_source
    if not node_data_source or not node_data_source.data:
        return

    node_data = node_data_source.data
    if ("x" in node_data and "y" in node_data and node_data.get("x") and node_data.get("y")) or not node_data.get(
        "index"
    ):
        return

    ordered_node_ids_from_source = node_data["index"]
    try:
        node_xs = [final_pos[node_id][0] for node_id in ordered_node_ids_from_source]
        node_ys = [final_pos[node_id][1] for node_id in ordered_node_ids_from_source]
    except KeyError:
        return

    node_data_source.data["x"] = node_xs
    node_data_source.data["y"] = node_ys


def _configure_selection_glyph(node_renderer: Any) -> None:
    if node_renderer.selection_glyph is None or not hasattr(node_renderer.selection_glyph, "size"):
        node_renderer.selection_glyph = Circle(
            radius="viz_radius_screen",
            radius_units="screen",
            fill_color="firebrick",
            fill_alpha=0.8,
            line_color="black",
            line_width=2,
        )
        return

    sel_glyph = node_renderer.selection_glyph
    if hasattr(sel_glyph, "size"):
        sel_glyph.size = "viz_size"
    elif hasattr(sel_glyph, "radius"):
        sel_glyph.radius = "viz_radius_screen"
        if hasattr(sel_glyph, "radius_units"):
            sel_glyph.radius_units = "screen"

    sel_glyph.fill_color = "firebrick"
    sel_glyph.line_width = 2


def _configure_node_renderer(graph_renderer: Any) -> None:
    main_node_glyph = graph_renderer.node_renderer.glyph
    main_node_glyph.size = "viz_size"
    main_node_glyph.fill_color = "viz_color"
    main_node_glyph.fill_alpha = 0.8
    main_node_glyph.line_color = "black"
    main_node_glyph.line_width = 0.5

    graph_renderer.node_renderer.hover_glyph = Circle(
        radius="viz_radius_screen",
        radius_units="screen",
        fill_color="orange",
        fill_alpha=0.8,
        line_color="black",
        line_width=2,
    )
    _configure_selection_glyph(graph_renderer.node_renderer)


def _configure_edge_renderer(graph_renderer: Any) -> None:
    graph_renderer.edge_renderer.glyph = MultiLine(line_color="#CCCCCC", line_alpha=0.8, line_width=1.5)
    graph_renderer.edge_renderer.hover_glyph = MultiLine(line_color="orange", line_width=2)
    graph_renderer.edge_renderer.selection_glyph = MultiLine(line_color="firebrick", line_width=2)


def _build_arrow_source_data(graph: nx.DiGraph, final_pos: dict) -> dict[str, list[float]]:
    arrow_source_data: dict[str, list[float]] = {"start_x": [], "start_y": [], "end_x": [], "end_y": []}

    for start_node, end_node in graph.edges():
        start_coords = final_pos[start_node]
        end_coords = final_pos[end_node]
        arrow_source_data["start_x"].append(start_coords[0])
        arrow_source_data["start_y"].append(start_coords[1])
        arrow_source_data["end_x"].append(end_coords[0])
        arrow_source_data["end_y"].append(end_coords[1])

    return arrow_source_data


def _add_arrow_renderer(plot: Any, graph: nx.DiGraph, final_pos: dict) -> None:
    arrow_source = ColumnDataSource(data=_build_arrow_source_data(graph, final_pos))
    arrow_head = OpenHead(line_color="gray", line_width=2, size=12)
    arrow_renderer = Arrow(
        end=arrow_head,
        source=arrow_source,
        x_start="start_x",
        y_start="start_y",
        x_end="end_x",
        y_end="end_y",
    )
    plot.add_layout(arrow_renderer)


def _configure_hover(plot: Any, graph_renderer: Any) -> None:
    hover_tool_instance = plot.select_one(HoverTool)
    if not hover_tool_instance:
        return

    hover_tool_instance.renderers = [graph_renderer.node_renderer]
    hover_tool_instance.tooltips = [
        ("Name", "@viz_label"),
        ("Type", "@viz_type"),
        ("Total Links", "@total_degree"),
        ("Incoming", "@in_degree"),
        ("Outgoing", "@out_degree"),
        ("ID", "@index"),
        ("Folder", "@folder"),
    ]


def draw_bokeh_graph(graph: nx.DiGraph, layout: str) -> None:
    _populate_node_visual_data(graph)

    final_pos, folder_rect_data = _build_bokeh_layout(graph, layout)
    plot, _folder_source = _create_bokeh_plot(folder_rect_data)
    graph_renderer = from_networkx(graph, final_pos)
    _sync_node_coordinates(graph_renderer, final_pos)
    _configure_node_renderer(graph_renderer)
    _configure_edge_renderer(graph_renderer)
    _add_arrow_renderer(plot, graph, final_pos)
    graph_renderer.selection_policy = NodesAndLinkedEdges()
    graph_renderer.inspection_policy = NodesAndLinkedEdges()
    _configure_hover(plot, graph_renderer)
    plot.renderers.append(graph_renderer)

    show(plot)
