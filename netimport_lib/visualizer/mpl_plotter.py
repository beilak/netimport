"""Matplotlib-based graph rendering."""

from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import Final, TypeAlias, cast

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


NodePosition: TypeAlias = tuple[float, float]
RawLayoutPositions: TypeAlias = Mapping[str, Sequence[float]]
MplLayoutBuilder: TypeAlias = Callable[[nx.DiGraph], RawLayoutPositions]

FREEZE_RANDOM_SEED: Final[int] = 42
MIN_NODE_SIZE: Final[int] = 2500
NODE_COLOR_MAP: Final[Mapping[str, str]] = MappingProxyType(
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


def _normalize_layout_positions(raw_positions: RawLayoutPositions) -> dict[str, NodePosition]:
    return {
        node_id: (float(position[0]), float(position[1]))
        for node_id, position in raw_positions.items()
    }


def _build_spring_layout(graph: nx.DiGraph) -> RawLayoutPositions:
    num_nodes = graph.number_of_nodes()
    optimal_k = float(4.0 / np.sqrt(num_nodes)) if num_nodes > 0 else 1.0

    return cast(
        "RawLayoutPositions",
        nx.spring_layout(
            graph,
            k=optimal_k,
            iterations=500,
            seed=FREEZE_RANDOM_SEED,
            scale=2,
            center=(0, 0),
        ),
    )


def _build_circular_layout(graph: nx.DiGraph) -> RawLayoutPositions:
    return cast("RawLayoutPositions", nx.circular_layout(graph))


def _build_shell_layout(graph: nx.DiGraph) -> RawLayoutPositions:
    return cast("RawLayoutPositions", nx.shell_layout(graph))


def _build_planar_layout(graph: nx.DiGraph) -> RawLayoutPositions:
    return cast("RawLayoutPositions", nx.planar_layout(graph))


MPL_LAYOUT_BUILDERS: Final[dict[str, MplLayoutBuilder]] = {
    "spring": _build_spring_layout,
    "circular": _build_circular_layout,
    "shell": _build_shell_layout,
    "planar_layout": _build_planar_layout,
}


def _build_layout_positions(graph: nx.DiGraph, layout: str) -> dict[str, NodePosition]:
    try:
        layout_builder = MPL_LAYOUT_BUILDERS[layout]
    except KeyError as exc:
        supported_layouts = ", ".join(MPL_LAYOUT_BUILDERS)
        raise ValueError(
            f"Unsupported Matplotlib layout '{layout}'. Supported layouts: {supported_layouts}."
        ) from exc

    return _normalize_layout_positions(layout_builder(graph))


def draw_graph_mpl(graph: nx.DiGraph, layout: str) -> None:
    """Render a dependency graph with Matplotlib."""
    plt.figure(figsize=(18, 12))

    positions = _build_layout_positions(graph, layout)
    normalized_positions = cast("Mapping[object, Sequence[float]]", positions)
    node_sizes = [MIN_NODE_SIZE + 2000 * graph.in_degree(node_id) for node_id in graph.nodes()]
    node_colors = [
        NODE_COLOR_MAP.get(str(graph.nodes[node_id].get("type", "unresolved")), "lightgray")
        for node_id in graph.nodes()
    ]
    node_labels = cast(
        "Mapping[object, str]",
        {
            str(node_id): str(graph.nodes[node_id].get("label", node_id))
            for node_id in graph.nodes()
        },
    )

    nx.draw_networkx_nodes(
        graph,
        normalized_positions,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.9,
    )
    nx.draw_networkx_labels(
        graph,
        normalized_positions,
        labels=node_labels,
        font_size=9,
        font_weight="bold",
    )
    nx.draw_networkx_edges(
        graph,
        normalized_positions,
        arrows=True,
        arrowstyle="->",
        style="--",
        arrowsize=20,
        edge_color="gray",
        width=1,
        node_size=node_sizes,
        connectionstyle="arc3,rad=0.05",
    )

    plt.title("Dependency graph", fontsize=16)
    plt.axis("off")
    plt.tight_layout()
    plt.show()
