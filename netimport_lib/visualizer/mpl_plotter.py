from collections.abc import Callable

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


FREEZ_RANDOM_SEED = 42


def _build_spring_layout(graph: nx.DiGraph) -> dict:
    num_nodes = len(graph.nodes())
    optimal_k = 4.0 / np.sqrt(num_nodes) if num_nodes > 0 else 1.0

    return nx.spring_layout(
        graph,
        k=optimal_k,
        iterations=500,
        seed=FREEZ_RANDOM_SEED,
        scale=2,
        center=(0, 0),
    )


MPL_LAYOUT_BUILDERS: dict[str, Callable[[nx.DiGraph], dict]] = {
    "spring": _build_spring_layout,
    "circular": nx.circular_layout,
    "shell": nx.shell_layout,
    "planar_layout": nx.planar_layout,
}


def _build_layout_positions(graph: nx.DiGraph, layout: str) -> dict:
    try:
        layout_builder = MPL_LAYOUT_BUILDERS[layout]
    except KeyError as exc:
        supported_layouts = ", ".join(MPL_LAYOUT_BUILDERS)
        raise ValueError(
            f"Unsupported Matplotlib layout '{layout}'. Supported layouts: {supported_layouts}."
        ) from exc

    return layout_builder(graph)


def draw_graph_mpl(graph: nx.DiGraph, layout: str) -> None:
    plt.figure(figsize=(18, 12))

    pos = _build_layout_positions(graph, layout)

    node_colors = []
    node_labels = {}
    color_map = {
        "project_file": "skyblue",
        "std_lib": "lightgreen",
        "external_lib": "salmon",
        "unresolved": "lightgray",
        "unresolved_relative": "silver",
    }
    min_node_size = 2500
    node_size = [min_node_size + 2000 * graph.in_degree(n) for n in graph.nodes()]

    for node, data in graph.nodes(data=True):
        node_colors.append(color_map.get(data.get("type", "unresolved"), "lightgray"))
        node_labels[node] = data.get("label", node)

    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=node_size, alpha=0.9)
    nx.draw_networkx_labels(graph, pos, labels=node_labels, font_size=9, font_weight="bold")
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
