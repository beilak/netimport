import networkx as nx

# from bokeh.models import (
#     Circle,
#     MultiLine,
#     NodesAndLinkedEdges,
#     NodesAndLinkedNodes,
#     HoverTool,
#     LabelSet,
# )
from bokeh.models import (
    Circle,
    HoverTool,
    LabelSet,
    MultiLine,
    NodesAndLinkedEdges,
    PointDrawTool,  # Инструмент для перетаскивания/редактирования точек
)
from bokeh.plotting import figure, from_networkx, show


FREEZ_RANDOM_SEED = 42


# TODO PointDrawTool не работает, надо чинить


def draw_bokeh_graph(G: nx.DiGraph, layout) -> None:
    # 0. Ваша карта цветов
    color_map = {
        "project_file": "skyblue",
        "std_lib": "lightgreen",
        "external_lib": "salmon",
        "unresolved": "lightgray",
        "unresolved_relative": "silver",
    }
    default_node_color = "red"
    # 2. Подготовка данных для Bokeh
    pos = nx.spring_layout(G, k=1.8, iterations=100, seed=FREEZ_RANDOM_SEED)

    node_ids_list = list(G.nodes())
    degrees = dict(G.degree())
    min_node_size_constant = 20
    label_padding = 20

    for node_id in node_ids_list:
        node_original_data = G.nodes[node_id]
        current_degree = degrees.get(node_id, 0)
        calculated_size = min_node_size_constant + current_degree * 10
        calculated_radius_screen = calculated_size / 2.0

        G.nodes[node_id]["viz_size"] = calculated_size
        G.nodes[node_id]["viz_radius_screen"] = calculated_radius_screen
        G.nodes[node_id]["viz_color"] = color_map.get(
            node_original_data.get("type", "unresolved"), default_node_color
        )
        G.nodes[node_id]["viz_label"] = node_original_data.get("label", str(node_id))
        G.nodes[node_id]["viz_degree"] = current_degree
        G.nodes[node_id]["viz_type"] = node_original_data.get("type", "unresolved")
        G.nodes[node_id]["viz_label_y_offset"] = (
            calculated_radius_screen + label_padding
        )

    # 3. Создание фигуры Bokeh
    # Добавляем 'point_draw' в список инструментов по умолчанию
    # Сделайте так:

    plot = figure(
        title="Интерактивный граф с перетаскиванием узлов",
        sizing_mode="scale_both",
        tools="pan,wheel_zoom,box_zoom,reset,save,tap,hover,point_draw",  # 'point_draw' добавлен
        active_drag="pan",  # 'pan' активен для перетаскивания по умолчанию
        active_inspect="hover",  # 'hover' активен для инспекции по умолчанию
        output_backend="webgl",  # Включаем аппаратное ускорение
    )

    graph_renderer = from_networkx(G, pos, scale=1, center=(0, 0))

    node_data_source = graph_renderer.node_renderer.data_source
    if node_data_source and node_data_source.data:
        node_data = node_data_source.data
        if (
            "x" not in node_data
            or "y" not in node_data
            or not node_data.get("x")
            or not node_data.get("y")
        ):
            if node_data.get("index"):
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
            else:
                pass
        # else:
        # print("Колонки 'x' и 'y' уже присутствуют и не пусты в data_source узлов.")
    else:
        pass
    # --- КОНЕЦ ЯВНОГО ДОБАВЛЕНИЯ X и Y ---

    if (
        graph_renderer.node_renderer.data_source
        and graph_renderer.node_renderer.data_source.data
    ):
        pass
    else:
        pass

    # 4. Настройка отображения узлов
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

    # 5. Настройка отображения ребер
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
    if point_draw_tool_instance:
        if (
            not point_draw_tool_instance.renderers
            or graph_renderer.node_renderer not in point_draw_tool_instance.renderers
        ):
            if not point_draw_tool_instance.renderers:
                point_draw_tool_instance.renderers = [graph_renderer.node_renderer]
            else:
                point_draw_tool_instance.renderers.append(graph_renderer.node_renderer)
    else:
        pass

    # 6. Добавление меток узлов (LabelSet)
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

    # 7. Добавление/настройка других инструментов интерактивности
    # Политики для TapTool и HoverTool
    graph_renderer.selection_policy = NodesAndLinkedEdges()
    graph_renderer.inspection_policy = NodesAndLinkedEdges()

    # HoverTool уже добавлен в `tools="...,hover,..."`
    hover_tool_instance = plot.select_one(HoverTool)
    if hover_tool_instance:
        hover_tool_instance.renderers = [
            graph_renderer.node_renderer
        ]  # Явно указываем рендерер
        hover_tool_instance.tooltips = [
            ("Name", "@viz_label"),
            ("Type", "@viz_type"),
            ("Links", "@viz_degree"),
            ("ID", "@index"),
            ("Folder", "@folder"),
        ]
    # TapTool также уже добавлен

    plot.renderers.append(graph_renderer)

    # 8. Отображение
    show(plot)
