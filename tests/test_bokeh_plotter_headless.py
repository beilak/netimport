from typing import TYPE_CHECKING, cast

from _pytest.monkeypatch import MonkeyPatch
from bokeh import models as bokeh_models
from bokeh.models.annotations import Arrow
from bokeh.models.renderers import GraphRenderer

from tests.bokeh_plotter_support.graphs import build_sample_graph
from tests.bokeh_plotter_support.names import BokehNames
from tests.bokeh_plotter_support.rendering import (
    draw_and_capture_plot,
    select_all_by_type,
    select_one_by_type,
)
from tests.bokeh_plotter_support.toolbar import (
    assert_primary_tool_counts,
    assert_secondary_tool_counts,
    assert_toolbar_layout,
    assert_toolbar_styles,
    assert_toolbar_tool_state,
)


if TYPE_CHECKING:
    from bokeh.models.css import InlineStyleSheet


def test_headless_draw_keeps_input_clean(monkeypatch: MonkeyPatch) -> None:
    graph = build_sample_graph()
    shown_plot, shown_plots = draw_and_capture_plot(monkeypatch, graph)

    assert len(shown_plots) == 1
    assert len(select_all_by_type(shown_plot, GraphRenderer)) == 1
    assert BokehNames.viz_size_field not in graph.nodes[BokehNames.pkg_a_file]


def test_draw_graph_configures_headless_contract(monkeypatch: MonkeyPatch) -> None:
    shown_plot, _shown_plots = draw_and_capture_plot(monkeypatch, build_sample_graph())
    hover_tool = cast(
        "bokeh_models.HoverTool",
        select_one_by_type(shown_plot, bokeh_models.HoverTool),
    )

    assert hover_tool.tooltips == [
        ("Name", "@viz_label"),
        ("Type", "@viz_type"),
        ("Total Links", "@total_degree"),
        ("Incoming", "@in_degree"),
        ("Outgoing", "@out_degree"),
        ("ID", "@index"),
        ("Folder", "@folder"),
    ]
    assert hover_tool.renderers is not None
    assert len(hover_tool.renderers) == 1
    assert select_one_by_type(shown_plot, bokeh_models.PanTool) is not None
    assert len(select_all_by_type(shown_plot, Arrow)) == 1


def test_draw_graph_uses_single_toolbar(monkeypatch: MonkeyPatch) -> None:
    shown_plot, _shown_plots = draw_and_capture_plot(monkeypatch, build_sample_graph())
    tool_type_names = [type(tool).__name__ for tool in shown_plot.tools]
    tap_tool = cast("bokeh_models.TapTool", select_one_by_type(shown_plot, bokeh_models.TapTool))
    wheel_zoom_tool = cast(
        "bokeh_models.WheelZoomTool",
        select_one_by_type(shown_plot, bokeh_models.WheelZoomTool),
    )

    assert_primary_tool_counts(tool_type_names)
    assert_secondary_tool_counts(tool_type_names)
    assert_toolbar_tool_state(shown_plot, tap_tool, wheel_zoom_tool)
    assert type(shown_plot.toolbar.active_drag).__name__ == "PanTool"


def test_draw_graph_toolbar_on_left(monkeypatch: MonkeyPatch) -> None:
    shown_plot, _shown_plots = draw_and_capture_plot(monkeypatch, build_sample_graph())
    toolbar_stylesheet = cast("InlineStyleSheet", shown_plot.toolbar.stylesheets[0])

    assert_toolbar_layout(shown_plot)
    assert_toolbar_styles(shown_plot, toolbar_stylesheet)
