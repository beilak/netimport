"""Visualizer registry and contracts."""

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import networkx as nx


GraphRenderFunc = Callable[[nx.DiGraph, str], None]


@dataclass(frozen=True, slots=True)
class GraphVisualizer:
    """Description of a supported graph visualizer backend."""

    name: str
    render: GraphRenderFunc
    supported_layouts: tuple[str, ...]
    default_layout: str


def _render_bokeh(graph: nx.DiGraph, layout: str) -> None:
    draw_bokeh_graph = importlib.import_module(
        "netimport_lib.visualizer.bokeh_plotter_v2"
    ).draw_bokeh_graph

    draw_bokeh_graph(graph, layout)


def _render_mpl(graph: nx.DiGraph, layout: str) -> None:
    draw_graph_mpl = importlib.import_module(
        "netimport_lib.visualizer.mpl_plotter"
    ).draw_graph_mpl

    draw_graph_mpl(graph, layout)


MPL_LAYOUTS: Final[tuple[str, ...]] = (
    "spring",
    "circular",
    "shell",
    "planar_layout",
)
BOKEH_LAYOUTS: Final[tuple[str, ...]] = ("constrained",)
GRAPH_VISUALIZERS: Final[dict[str, GraphVisualizer]] = {
    "bokeh": GraphVisualizer(
        name="bokeh",
        render=_render_bokeh,
        supported_layouts=BOKEH_LAYOUTS,
        default_layout="constrained",
    ),
    "mpl": GraphVisualizer(
        name="mpl",
        render=_render_mpl,
        supported_layouts=MPL_LAYOUTS,
        default_layout="spring",
    ),
}
DEFAULT_VISUALIZER: Final[str] = "bokeh"
GRAPH_VISUALIZER_NAMES: Final[tuple[str, ...]] = tuple(GRAPH_VISUALIZERS)
GRAPH_LAYOUT_CHOICES: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(
        layout_name
        for visualizer in GRAPH_VISUALIZERS.values()
        for layout_name in visualizer.supported_layouts
    )
)

__all__ = [
    "BOKEH_LAYOUTS",
    "DEFAULT_VISUALIZER",
    "GRAPH_LAYOUT_CHOICES",
    "GRAPH_VISUALIZERS",
    "GRAPH_VISUALIZER_NAMES",
    "MPL_LAYOUTS",
    "GraphVisualizer",
]
