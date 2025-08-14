import networkx as nx
from bokeh.models import (
    Circle,
    HoverTool,
    LabelSet,
    MultiLine,
    NodesAndLinkedEdges,
    PointDrawTool,
)
from bokeh.plotting import figure, from_networkx, show


FREEZ_RANDOM_SEED = 42


def draw_bokeh_graph(graph: nx.DiGraph, layout: str) -> None:
    color_map = {
        "project_file": "skyblue",
        "std_lib": "lightgreen",
        "external_lib": "salmon",
        "unresolved": "lightgray",
        "unresolved_relative": "silver",
    }
    default_node_color = "red"
    pos = nx.spring_layout(graph, k=1.8, iterations=100, seed=FREEZ_RANDOM_SEED)

    node_ids_list = list(graph.nodes())
    degrees = dict(graph.degree())
    min_node_size_constant = 20
    label_padding = 20

    for node_id in node_ids_list:
        node_original_data = graph.nodes[node_id]
        current_degree = degrees.get(node_id, 0)
        calculated_size = min_node_size_constant + current_degree * 10
        calculated_radius_screen = calculated_size / 2.0

        graph.nodes[node_id]["viz_size"] = calculated_size
        graph.nodes[node_id]["viz_radius_screen"] = calculated_radius_screen
        graph.nodes[node_id]["viz_color"] = color_map.get(
            node_original_data.get("type", "unresolved"), default_node_color
        )
        graph.nodes[node_id]["viz_label"] = node_original_data.get("label", str(node_id))
        graph.nodes[node_id]["viz_degree"] = current_degree
        graph.nodes[node_id]["viz_type"] = node_original_data.get("type", "unresolved")
        graph.nodes[node_id]["viz_label_y_offset"] = (
            calculated_radius_screen + label_padding
        )

    plot = figure(
        title="Interactive graph with draggable nodes",
        sizing_mode="scale_both",
        tools="pan,wheel_zoom,box_zoom,reset,save,tap,hover,point_draw",
        active_drag="pan",
        active_inspect="hover",
        output_backend="webgl",
    )

    graph_renderer = from_networkx(graph, pos, scale=1, center=(0, 0))

    node_data_source = graph_renderer.node_renderer.data_source
    if node_data_source and node_data_source.data:
        node_data = node_data_source.data
        if (
            "x" not in node_data
            or "y" not in node_data
            or not node_data.get("x")
            or not node_data.get("y")
        ) and node_data.get("index"):
            ordered_node_ids_from_source = node_data["index"]
            try:
                node_xs = [
                    pos[node_id][0] for node_id in ordered_node_ids_from_source
                ]
                node_ys = [
                    pos[node_id][1] for node_id in ordered_node_ids_from_source
                ]
                node_data_source.data["x"] = node_xs
                node_data_source.data["y"] = node_ys
            except KeyError:
                pass
            except Exception:
                pass

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

    if graph_renderer.node_renderer.selection_glyph is None or not hasattr(
        graph_renderer.node_renderer.selection_glyph, "size"
    ):
        graph_renderer.node_renderer.selection_glyph = Circle(
            radius="viz_radius_screen",
            radius_units="screen",
            fill_color="firebrick",
            fill_alpha=0.8,
            line_color="black",
            line_width=2,
        )
    else:
        sel_glyph = graph_renderer.node_renderer.selection_glyph
        if hasattr(sel_glyph, "size"):
            sel_glyph.size = "viz_size"
        elif hasattr(sel_glyph, "radius"):
            sel_glyph.radius = "viz_radius_screen"
            if hasattr(sel_glyph, "radius_units"):
                sel_glyph.radius_units = "screen"
        sel_glyph.fill_color = "firebrick"
        sel_glyph.line_width = 2

    graph_renderer.edge_renderer.glyph = MultiLine(
        line_color="#CCCCCC", line_alpha=0.8, line_width=1
    )
    graph_renderer.edge_renderer.hover_glyph = MultiLine(
        line_color="orange", line_width=2
    )
    graph_renderer.edge_renderer.selection_glyph = MultiLine(
        line_color="firebrick", line_width=2
    )

    point_draw_tool_instance = plot.select_one(PointDrawTool)
    if point_draw_tool_instance and (
        not point_draw_tool_instance.renderers
        or graph_renderer.node_renderer not in point_draw_tool_instance.renderers
    ):
        if not point_draw_tool_instance.renderers:
            point_draw_tool_instance.renderers = [graph_renderer.node_renderer]
        else:
            point_draw_tool_instance.renderers.append(graph_renderer.node_renderer)

    labels = LabelSet(
        x="x",
        y="y",
        text="viz_label",
        source=graph_renderer.node_renderer.data_source,
        text_font_size="11pt",
        text_color="black",
        text_align="center",
        text_baseline="top",
        y_offset="viz_label_y_offset",
        x_offset=0,
        text_alpha=0.7,
    )
    plot.add_layout(labels)

    graph_renderer.selection_policy = NodesAndLinkedEdges()
    graph_renderer.inspection_policy = NodesAndLinkedEdges()

    hover_tool_instance = plot.select_one(HoverTool)
    if hover_tool_instance:
        hover_tool_instance.renderers = [graph_renderer.node_renderer]
        hover_tool_instance.tooltips = [
            ("Name", "@viz_label"),
            ("Type", "@viz_type"),
            ("Links", "@viz_degree"),
            ("ID", "@index"),
            ("Folder", "@folder"),
        ]

    plot.renderers.append(graph_renderer)

    show(plot)
