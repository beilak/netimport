import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


FREEZ_RANDOM_SEED = 42


def draw_graph_mpl(graph: nx.DiGraph, layout) -> None:
    plt.figure(figsize=(18, 12))

    # TODO inject type of resolving node position algo
    # TODO refact IF's
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
    min_node_size = 2500  # TODO inject
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
