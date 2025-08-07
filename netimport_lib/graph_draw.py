import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go

from bokeh.plotting import figure, from_networkx, show
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
    MultiLine,
    NodesAndLinkedEdges,
    HoverTool,
    LabelSet,
)
from bokeh.models import (
    PointDrawTool # Инструмент для перетаскивания/редактирования точек
)

FREEZ_RANDOM_SEED = 42


def draw_graph(graph: nx.DiGraph, layout):
    plt.figure(figsize=(18, 12))

    # ToDo inject type of resolving node position algo
    # ToDo refact IF's
    if layout == "spring":
        num_nodes = len(graph.nodes())
        optimal_k = 4.0 / np.sqrt(num_nodes) if num_nodes > 0 else 1.0

        pos = nx.spring_layout(
            graph,
            k=optimal_k,
            iterations=500,
            seed=FREEZ_RANDOM_SEED,
            scale=2,
            center=(0, 0),
        )
    # pos = nx.circular_layout(graph)
    # pos = nx.shell_layout(graph)
    # pos = nx.fruchterman_reingold_layout(graph)

    if layout == "planar_layout":
        pos = nx.planar_layout(graph)

    node_colors = []
    node_labels = {}
    color_map = {
        "project_file": "skyblue",
        "std_lib": "lightgreen",
        "external_lib": "salmon",
        "unresolved": "lightgray",
        "unresolved_relative": "silver",
    }
    min_node_size = 2500  # ToDo inject
    node_size = [min_node_size + 2000 * graph.in_degree(n) for n in graph.nodes()]

    for node, data in graph.nodes(data=True):
        node_colors.append(color_map.get(data.get("type", "unresolved"), "lightgray"))
        node_labels[node] = data.get("label", node)

    nx.draw_networkx_nodes(
        graph, pos, node_color=node_colors, node_size=node_size, alpha=0.9
    )
    nx.draw_networkx_labels(
        graph, pos, labels=node_labels, font_size=9, font_weight="bold"
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        arrows=True,
        arrowstyle="->",
        style="--",
        arrowsize=20,
        edge_color="gray",
        width=1,
        node_size=node_size,
        connectionstyle="arc3,rad=0.05",
    )

    plt.title("Dependency graph", fontsize=16)
    plt.axis("off")
    plt.tight_layout()
    plt.show()


def draw_plotly_graph(graph: nx.DiGraph, layout):
    pos = nx.spring_layout(graph, k=0.5, iterations=50)  # Получаем позиции узлов

    edge_x = []
    edge_y = []
    for edge in graph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])  # None для разрыва линии
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=0.5, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    node_x = []
    node_y = []
    node_text = []
    for node, node_data in graph.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        label = node_data.get("label", node)
        node_text.append(f"{label}")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",  # Отображать и маркеры, и текст
        hoverinfo="text",
        text=node_text,
        textposition="top center",
        marker=dict(
            showscale=False,  # Можно добавить цветовую шкалу, если узлы окрашены
            # colorscale='YlGnBu',
            reversescale=True,
            color=[],  # здесь можно задать цвета для каждого узла
            size=10,
            # colorbar=dict(
            #     thickness=15,
            #     title='Node Connections',
            #     xanchor='left',
            #     titleside='right'
            # ),
            line_width=2,
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="<br>Интерактивный граф на Plotly",
            font_size=16,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )
    fig.show()
    # fig.write_html("plotly_graph.html") # Для сохранения в файл


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
    pos = nx.spring_layout(G, k=0.8, iterations=100, seed=42)
    print("--- POS dictionary ---")
    print(pos)
    print("----------------------")

    node_ids_list = list(G.nodes())
    degrees = dict(G.degree())
    min_node_size_constant = 12
    label_padding = 5

    for node_id in node_ids_list:
        node_original_data = G.nodes[node_id]
        current_degree = degrees.get(node_id, 0)
        calculated_size = min_node_size_constant + current_degree * 10
        calculated_radius_screen = calculated_size / 2.0

        G.nodes[node_id]['viz_size'] = calculated_size
        G.nodes[node_id]['viz_radius_screen'] = calculated_radius_screen
        G.nodes[node_id]['viz_color'] = color_map.get(node_original_data.get('type', 'unresolved'), default_node_color)
        G.nodes[node_id]['viz_label'] = node_original_data.get('label', str(node_id))
        G.nodes[node_id]['viz_degree'] = current_degree
        G.nodes[node_id]['viz_type'] = node_original_data.get('type', 'unresolved')
        G.nodes[node_id]['viz_label_y_offset'] = calculated_radius_screen + label_padding

    # 3. Создание фигуры Bokeh
    # Добавляем 'point_draw' в список инструментов по умолчанию
    plot = figure(
        title="Интерактивный граф с перетаскиванием узлов",
        sizing_mode="stretch_both",
        tools="pan,wheel_zoom,box_zoom,reset,save,tap,hover,point_draw", # 'point_draw' добавлен
        active_drag="pan",  # 'pan' активен для перетаскивания по умолчанию
        active_inspect="hover" # 'hover' активен для инспекции по умолчанию
    )

    graph_renderer = from_networkx(G, pos, scale=1, center=(0,0))

    # --- ЯВНОЕ ДОБАВЛЕНИЕ X и Y (ЕСЛИ from_networkx НЕ СПРАВИЛАСЬ) ---
    node_data_source = graph_renderer.node_renderer.data_source
    if node_data_source and node_data_source.data:
        node_data = node_data_source.data
        if 'x' not in node_data or 'y' not in node_data or \
                not node_data.get('x') or not node_data.get('y'):
            print("!!! Колонки 'x' и 'y' отсутствуют или пусты, добавляем/обновляем вручную !!!")
            if 'index' in node_data and node_data['index']:
                ordered_node_ids_from_source = node_data['index']
                try:
                    node_xs = [pos[node_id][0] for node_id in ordered_node_ids_from_source]
                    node_ys = [pos[node_id][1] for node_id in ordered_node_ids_from_source]
                    node_data_source.data['x'] = node_xs
                    node_data_source.data['y'] = node_ys
                    print("Колонки 'x' и 'y' добавлены/обновлены по 'index'.")
                except KeyError as e:
                    print(f"!!! Ошибка KeyError при доступе к pos по ID из 'index': {e}. Проверьте соответствие ID.")
                except Exception as e:
                    print(f"!!! Другая ошибка при формировании x, y по 'index': {e}")
            else:
                print("!!! Колонка 'index' отсутствует/пуста в data_source узлов. Не удалось добавить x,y.")
        # else:
        # print("Колонки 'x' и 'y' уже присутствуют и не пусты в data_source узлов.")
    else:
        print("!!! Node renderer data source is None или пуст! Невозможно добавить x, y.")
    # --- КОНЕЦ ЯВНОГО ДОБАВЛЕНИЯ X и Y ---

    print("--- Node Renderer Data Source (ПОСЛЕ возможного добавления x,y) ---")
    if graph_renderer.node_renderer.data_source and graph_renderer.node_renderer.data_source.data:
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
        radius="viz_radius_screen", radius_units="screen",
        fill_color="orange", fill_alpha=0.8, line_color="black", line_width=2
    )

    if graph_renderer.node_renderer.selection_glyph is None or not hasattr(graph_renderer.node_renderer.selection_glyph, 'size'):
        graph_renderer.node_renderer.selection_glyph = Circle(
            radius="viz_radius_screen", radius_units="screen",
            fill_color="firebrick", fill_alpha=0.8, line_color="black", line_width=2
        )
    else:
        sel_glyph = graph_renderer.node_renderer.selection_glyph
        if hasattr(sel_glyph, 'size'):
            sel_glyph.size = "viz_size"
        elif hasattr(sel_glyph, 'radius'):
            sel_glyph.radius = "viz_radius_screen"
            if hasattr(sel_glyph, 'radius_units'):
                sel_glyph.radius_units = "screen"
        sel_glyph.fill_color = "firebrick"
        sel_glyph.line_width = 2

    # 5. Настройка отображения ребер
    graph_renderer.edge_renderer.glyph = MultiLine(
        line_color="#CCCCCC", line_alpha=0.8, line_width=1
    )
    graph_renderer.edge_renderer.hover_glyph = MultiLine(line_color="orange", line_width=2)
    graph_renderer.edge_renderer.selection_glyph = MultiLine(line_color="firebrick", line_width=2)


    # --- ИНТЕРАКТИВНОЕ ПЕРЕТАСКИВАНИЕ УЗЛОВ ---
    # PointDrawTool был добавлен в `tools` при создании фигуры.
    # Теперь мы его получаем и настраиваем (если это необходимо).
    point_draw_tool_instance = plot.select_one(PointDrawTool)
    if point_draw_tool_instance:
        # Убедимся, что инструмент знает, с какими рендерерами узлов работать.
        # Если renderers пуст, он попытается работать со всеми подходящими.
        # Явное указание - хорошая практика.
        if not point_draw_tool_instance.renderers or graph_renderer.node_renderer not in point_draw_tool_instance.renderers:
            # Если список renderers пуст или нашего рендерера там нет, добавляем
            if not point_draw_tool_instance.renderers: # если список пуст, можно просто присвоить
                point_draw_tool_instance.renderers = [graph_renderer.node_renderer]
            else: # если не пуст, добавляем в существующий список
                point_draw_tool_instance.renderers.append(graph_renderer.node_renderer)
            print("PointDrawTool настроен на node_renderer для перетаскивания.")
        # По умолчанию drag=True, add=True. Если нужно только перетаскивание, можно выключить добавление:
        # point_draw_tool_instance.add = False
    else:
        print("!!! PointDrawTool не найден. Убедитесь, что 'point_draw' есть в строке tools при создании figure.")


    # 6. Добавление меток узлов (LabelSet)
    labels = LabelSet(
        x='x', y='y',
        text='viz_label',
        source=graph_renderer.node_renderer.data_source,
        text_font_size="9pt",
        text_color="black",
        text_align='center',
        text_baseline='top',
        y_offset='viz_label_y_offset',
        x_offset=0
    )
    plot.add_layout(labels)

    # 7. Добавление/настройка других инструментов интерактивности
    # Политики для TapTool и HoverTool
    graph_renderer.selection_policy = NodesAndLinkedEdges()
    graph_renderer.inspection_policy = NodesAndLinkedEdges()

    # HoverTool уже добавлен в `tools="...,hover,..."`
    hover_tool_instance = plot.select_one(HoverTool)
    if hover_tool_instance:
        hover_tool_instance.renderers = [graph_renderer.node_renderer] # Явно указываем рендерер
        hover_tool_instance.tooltips = [
            ("Имя", "@viz_label"), ("Тип", "@viz_type"),
            ("Связей", "@viz_degree"), ("ID", "@index")
        ]
    # TapTool также уже добавлен

    plot.renderers.append(graph_renderer)

    # 8. Отображение
    show(plot)