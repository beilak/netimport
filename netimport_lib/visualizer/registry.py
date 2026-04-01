"""Visualizer registry and contracts."""

import importlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

import networkx as nx


GraphRenderFunc = Callable[[nx.DiGraph, str], str | None]


@dataclass(frozen=True, slots=True)
class GraphVisualizer:
    """Description of a supported graph visualizer backend."""

    name: str
    render: GraphRenderFunc
    supported_layouts: tuple[str, ...]
    default_layout: str


def _render_bokeh(graph: nx.DiGraph, layout: str) -> str | None:
    draw_bokeh_graph = cast(
        "GraphRenderFunc",
        importlib.import_module("netimport_lib.visualizer.bokeh_plotter").draw_bokeh_graph,
    )
    return draw_bokeh_graph(graph, layout)


GRAPH_VISUALIZERS: Final[Mapping[str, GraphVisualizer]] = MappingProxyType(
    {
        "bokeh": GraphVisualizer(
            name="bokeh",
            render=_render_bokeh,
            supported_layouts=("constrained",),
            default_layout="constrained",
        )
    }
)
DEFAULT_VISUALIZER: Final[str] = "bokeh"
GRAPH_VISUALIZER_NAMES: Final[tuple[str, ...]] = tuple(GRAPH_VISUALIZERS)
GRAPH_LAYOUT_CHOICES: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(
        layout_name
        for visualizer in GRAPH_VISUALIZERS.values()
        for layout_name in visualizer.supported_layouts
    )
)
