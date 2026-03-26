from collections.abc import Callable
from dataclasses import dataclass

import networkx as nx

from netimport_lib.visualizer.bokeh_plotter_v2 import draw_bokeh_graph
from netimport_lib.visualizer.mpl_plotter import draw_graph_mpl


GraphRenderFunc = Callable[[nx.DiGraph, str], None]

MPL_LAYOUTS: tuple[str, ...] = (
    "spring",
    "circular",
    "shell",
    "planar_layout",
)
BOKEH_LAYOUTS: tuple[str, ...] = ("constrained",)


@dataclass(frozen=True)
class GraphVisualizer:
    name: str
    render: GraphRenderFunc
    supported_layouts: tuple[str, ...]
    default_layout: str


GRAPH_VISUALIZERS: dict[str, GraphVisualizer] = {
    "bokeh": GraphVisualizer(
        name="bokeh",
        render=draw_bokeh_graph,
        supported_layouts=BOKEH_LAYOUTS,
        default_layout="constrained",
    ),
    "mpl": GraphVisualizer(
        name="mpl",
        render=draw_graph_mpl,
        supported_layouts=MPL_LAYOUTS,
        default_layout="spring",
    ),
}

DEFAULT_VISUALIZER = "bokeh"
GRAPH_VISUALIZER_NAMES: tuple[str, ...] = tuple(GRAPH_VISUALIZERS)
GRAPH_LAYOUT_CHOICES: tuple[str, ...] = tuple(
    dict.fromkeys(
        layout_name
        for visualizer in GRAPH_VISUALIZERS.values()
        for layout_name in visualizer.supported_layouts
    )
)
