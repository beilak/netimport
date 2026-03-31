from typing import TYPE_CHECKING, cast

import networkx as nx
from _pytest.monkeypatch import MonkeyPatch

from netimport_lib.visualizer import bokeh_plotter
from tests.bokeh_plotter_support.names import BokehNames


if TYPE_CHECKING:
    from bokeh.plotting._figure import figure as figure_model


def half(numeric_value: float) -> float:
    return numeric_value / BokehNames.half_divisor


def select_one_by_type(plot: "figure_model", model_type: object) -> object | None:
    return plot.select_one({BokehNames.type_query_key: model_type})


def select_all_by_type(plot: "figure_model", model_type: object) -> list[object]:
    return list(plot.select({BokehNames.type_query_key: model_type}))


def capture_rendered_plots(monkeypatch: MonkeyPatch) -> list[object]:
    shown_plots: list[object] = []
    monkeypatch.setattr(bokeh_plotter, BokehNames.present_plot_attr, shown_plots.append)
    return shown_plots


def first_rendered_plot(shown_plots: list[object]) -> "figure_model":
    return cast("figure_model", shown_plots[0])


def rendered_plot_at(shown_plots: list[object], index: int) -> "figure_model":
    return cast("figure_model", shown_plots[index])


def draw_and_capture_plot(
    monkeypatch: MonkeyPatch,
    graph: nx.DiGraph,
) -> tuple["figure_model", list[object]]:
    shown_plots = capture_rendered_plots(monkeypatch)
    bokeh_plotter.draw_bokeh_graph(graph, BokehNames.constrained_layout)
    return first_rendered_plot(shown_plots), shown_plots

