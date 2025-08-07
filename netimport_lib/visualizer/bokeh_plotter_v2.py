import networkx as nx
from bokeh.models import ColumnDataSource

# from bokeh.models import (
#     Circle,
#     MultiLine,
#     NodesAndLinkedEdges,
#     NodesAndLinkedNodes,
#     HoverTool,
#     LabelSet,
# )

FREEZ_RANDOM_SEED = 42


from collections import defaultdict


def create_constrained_layout(G, FOLDER_LAYOUT_K=2, NODE_LAYOUT_K=0.5):
    """
    Создает двухуровневую раскладку: сначала для папок, потом для файлов внутри них.

    :param G: Исходный граф NetworkX с атрибутом 'folder' у узлов.
    :param FOLDER_LAYOUT_K: Параметр 'k' для раскладки папок (влияет на расстояние между папками).
    :param NODE_LAYOUT_K: Параметр 'k' для раскладки файлов внутри папки.
    :return: Словарь с финальными координатами узлов и словарь с данными для отрисовки папок.
    """
    # 1. Группируем узлы по папкам
    folder_to_nodes = defaultdict(list)
    root_folder_nodes = []
    for node, data in G.nodes(data=True):
        if data["is_root_folder"]:
            root_folder_nodes.append(node)
        else:
            folder_to_nodes[data["folder"]].append(node)

    # normal_folders = {
    #     name: nodes
    #     for name, nodes in folder_to_nodes.items()
    #     if name != project_root_name
    # }
    # root_folder_nodes = folder_to_nodes.get(project_root_name, [])

    unique_folders = list(folder_to_nodes.keys())

    # 2. Создаем мета-граф папок и его раскладку
    folder_graph = nx.Graph()
    folder_graph.add_nodes_from(unique_folders)
    # Можно добавить ребра между папками, если между их файлами есть связи,
    # но для простоты начнем с раскладки несвязанных папок.

    # Раскладка для папок определяет "центры" областей
    # Умножаем на большой коэффициент, чтобы разнести папки далеко друг от друга
    folder_pos = nx.spring_layout(
        folder_graph,
        k=FOLDER_LAYOUT_K,
        iterations=100,
        seed=FREEZ_RANDOM_SEED,
        scale=10,
    )

    # 3. Рассчитываем локальные раскладки и смещаем их
    final_pos = {}
    # folder_bounds = {}  # Здесь будем хранить границы для отрисовки прямоугольников

    for folder_name, nodes_in_folder in folder_to_nodes.items():
        # Создаем подграф только из узлов этой папки
        subgraph = G.subgraph(nodes_in_folder)

        # Рассчитываем локальную раскладку для файлов (вокруг 0,0)
        local_pos = nx.spring_layout(
            subgraph, k=NODE_LAYOUT_K, iterations=50, seed=FREEZ_RANDOM_SEED
        )

        # Получаем центр области для этой папки из мета-раскладки
        folder_center_x, folder_center_y = folder_pos[folder_name]

        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")

        # Смещаем локальные координаты каждого узла и добавляем в финальный словарь
        for node, (x, y) in local_pos.items():
            global_x = x + folder_center_x
            global_y = y + folder_center_y
            final_pos[node] = (global_x, global_y)

            # Обновляем границы для будущего прямоугольника
            min_x, max_x = min(min_x, global_x), max(max_x, global_x)
            min_y, max_y = min(min_y, global_y), max(max_y, global_y)

    # 4. Рассчитываем данные для отрисовки прямоугольников
    PADDING = 0.5  # Отступ внутри прямоугольника
    folder_rect_data = defaultdict(list)
    for folder_name, nodes in folder_to_nodes.items():
        # Находим границы по уже рассчитанным глобальным координатам
        coords = [final_pos[n] for n in nodes]
        if not coords:
            continue

        min_x = min(c[0] for c in coords) - PADDING
        max_x = max(c[0] for c in coords) + PADDING
        min_y = min(c[1] for c in coords) - PADDING
        max_y = max(c[1] for c in coords) + PADDING

        folder_rect_data["x"].append((min_x + max_x) / 2)  # Центр X
        folder_rect_data["y"].append((min_y + max_y) / 2)  # Центр Y
        # folder_rect_data["y"].append(max_y)
        folder_rect_data["width"].append((max_x - min_x) + 3)
        folder_rect_data["height"].append((max_y - min_y) + 3)
        folder_rect_data["name"].append(folder_name)
        folder_rect_data["color"].append("#E8E8E8")  # Цвет фона папки

    if root_folder_nodes:
        root_subgraph = G.subgraph(root_folder_nodes)
        # Рассчитываем их раскладку вокруг центра (0,0). Можно увеличить scale,
        # чтобы они заняли больше места, если их много.
        root_pos = nx.spring_layout(
            root_subgraph,
            k=NODE_LAYOUT_K,
            iterations=50,
            seed=FREEZ_RANDOM_SEED,
            scale=5,  # Даем им больше места
            center=(0, 0),
        )
        final_pos.update(root_pos)

    return final_pos, folder_rect_data


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


# ToDo PointDrawTool не работает, надо чинить


def draw_bokeh_graph(G: nx.DiGraph, layout):
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
    print("--- POS dictionary ---")
    print(pos)
    print("----------------------")

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

    # --- Шаг 2: Создание раскладки ---
    final_pos, folder_rect_data = create_constrained_layout(G)

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

    folder_source = ColumnDataSource(data=folder_rect_data)

    # Рисуем сами прямоугольники
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
        level="underlay",  # Важно, чтобы прямоугольники были под узлами и ребрами
    )

    # Добавляем подписи к папкам
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
        level="overlay",  # Поверх всего
    )
    plot.add_layout(folder_labels)

    # graph_renderer = from_networkx(G, pos, scale=1, center=(0, 0))
    graph_renderer = from_networkx(G, final_pos)

    node_data_source = graph_renderer.node_renderer.data_source
    if node_data_source and node_data_source.data:
        node_data = node_data_source.data
        if (
            "x" not in node_data
            or "y" not in node_data
            or not node_data.get("x")
            or not node_data.get("y")
        ):
            print(
                "!!! Колонки 'x' и 'y' отсутствуют или пусты, добавляем/обновляем вручную !!!"
            )
            if "index" in node_data and node_data["index"]:
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
                    print("Колонки 'x' и 'y' добавлены/обновлены по 'index'.")
                except KeyError as e:
                    print(
                        f"!!! Ошибка KeyError при доступе к pos по ID из 'index': {e}. Проверьте соответствие ID."
                    )
                except Exception as e:
                    print(f"!!! Другая ошибка при формировании x, y по 'index': {e}")
            else:
                print(
                    "!!! Колонка 'index' отсутствует/пуста в data_source узлов. Не удалось добавить x,y."
                )
        # else:
        # print("Колонки 'x' и 'y' уже присутствуют и не пусты в data_source узлов.")
    else:
        print(
            "!!! Node renderer data source is None или пуст! Невозможно добавить x, y."
        )
    # --- КОНЕЦ ЯВНОГО ДОБАВЛЕНИЯ X и Y ---

    print("--- Node Renderer Data Source (ПОСЛЕ возможного добавления x,y) ---")
    if (
        graph_renderer.node_renderer.data_source
        and graph_renderer.node_renderer.data_source.data
    ):
        print(graph_renderer.node_renderer.data_source.data)
    else:
        print("Node renderer data source is None или пуст!")
    print("-----------------------------------------------------------------")

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
            print("PointDrawTool настроен на node_renderer для перетаскивания.")
    else:
        print(
            "!!! PointDrawTool не найден. Убедитесь, что 'point_draw' есть в строке tools при создании figure."
        )

    # # 6. Добавление меток узлов (LabelSet)
    # labels = LabelSet(
    #     x="x",
    #     y="y",
    #     text="viz_label",
    #     source=graph_renderer.node_renderer.data_source,
    #     text_font_size="11pt",
    #     text_color="black",
    #     text_align="center",
    #     text_baseline="top",
    #     y_offset="viz_label_y_offset",
    #     x_offset=0,
    #     text_alpha=0.7,
    # )
    # plot.add_layout(labels)

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
