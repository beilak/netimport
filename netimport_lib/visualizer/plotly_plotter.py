import networkx as nx
import plotly.graph_objects as go


FREEZ_RANDOM_SEED = 42


def draw_plotly_graph(graph: nx.DiGraph, layout) -> None:
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
        line={"width": 0.5, "color": "#888"},
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
        marker={
            "showscale": False,  # Можно добавить цветовую шкалу, если узлы окрашены
            # colorscale='YlGnBu',
            "reversescale": True,
            "color": [],  # здесь можно задать цвета для каждого узла
            "size": 10,
            # colorbar=dict(
            #     thickness=15,
            #     title='Node Connections',
            #     xanchor='left',
            #     titleside='right'
            # ),
            "line_width": 2,
        },
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="<br>Интерактивный граф на Plotly",
            font_size=16,
            showlegend=False,
            hovermode="closest",
            margin={"b": 20, "l": 5, "r": 5, "t": 40},
            xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        ),
    )
    fig.show()
