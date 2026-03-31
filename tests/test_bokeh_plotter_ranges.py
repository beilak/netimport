from typing import Any, cast

import pytest
from _pytest.monkeypatch import MonkeyPatch
from bokeh.models.renderers import GraphRenderer

from netimport_lib.visualizer import bokeh_plotter
from tests.bokeh_plotter_support.graphs import build_hub_graph, build_single_folder_graph
from tests.bokeh_plotter_support.names import BokehNames
from tests.bokeh_plotter_support.plot_assertions import (
    assert_render_covers_bounds,
    plot_dimensions,
)
from tests.bokeh_plotter_support.rendering import (
    capture_rendered_plots,
    draw_and_capture_plot,
    first_rendered_plot,
    rendered_plot_at,
    select_one_by_type,
)
from tests.bokeh_plotter_support.toolbar import assert_large_graph_edge_contract


def test_larger_hub_expands_plot_dimensions(monkeypatch: MonkeyPatch) -> None:
    shown_plots = capture_rendered_plots(monkeypatch)

    bokeh_plotter.draw_bokeh_graph(
        build_single_folder_graph(BokehNames.chain_comparison_node_count),
        BokehNames.constrained_layout,
    )
    bokeh_plotter.draw_bokeh_graph(
        build_hub_graph(BokehNames.hub_comparison_leaf_count),
        BokehNames.constrained_layout,
    )

    chain_width, chain_height = plot_dimensions(first_rendered_plot(shown_plots))
    hub_width, hub_height = plot_dimensions(rendered_plot_at(shown_plots, 1))

    assert hub_width > chain_width
    assert hub_height >= chain_height


def test_initial_ranges_cover_full_layout(monkeypatch: MonkeyPatch) -> None:
    shown_plots = capture_rendered_plots(monkeypatch)
    render_data = bokeh_plotter.prepare_bokeh_render(
        build_hub_graph(BokehNames.range_coverage_leaf_count),
        BokehNames.constrained_layout,
    )

    bokeh_plotter.draw_bokeh_graph(
        build_hub_graph(BokehNames.range_coverage_leaf_count),
        BokehNames.constrained_layout,
    )

    assert_render_covers_bounds(first_rendered_plot(shown_plots), render_data)


def test_large_graph_uses_lighter_edge_style(monkeypatch: MonkeyPatch) -> None:
    shown_plot, _shown_plots = draw_and_capture_plot(
        monkeypatch,
        build_hub_graph(BokehNames.light_edge_leaf_count),
    )
    graph_renderer = cast(
        "Any",
        select_one_by_type(shown_plot, GraphRenderer),
    )

    assert_large_graph_edge_contract(shown_plot)
    assert graph_renderer.edge_renderer.glyph.line_alpha == pytest.approx(
        bokeh_plotter.MEDIUM_EDGE_STYLE.line_alpha,
    )
    assert graph_renderer.edge_renderer.glyph.line_width == pytest.approx(1.0)


def test_large_graph_uses_larger_canvas(monkeypatch: MonkeyPatch) -> None:
    shown_plots = capture_rendered_plots(monkeypatch)

    bokeh_plotter.draw_bokeh_graph(build_single_folder_graph(4), BokehNames.constrained_layout)
    bokeh_plotter.draw_bokeh_graph(
        build_single_folder_graph(BokehNames.large_graph_node_count),
        BokehNames.constrained_layout,
    )

    small_width, small_height = plot_dimensions(first_rendered_plot(shown_plots))
    large_width, large_height = plot_dimensions(rendered_plot_at(shown_plots, 1))

    assert large_width > small_width
    assert large_height > small_height
