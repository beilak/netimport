from typing import TYPE_CHECKING, cast

import pytest
from bokeh import models as bokeh_models
from bokeh.models.annotations import Arrow

from tests.bokeh_plotter_support.names import BokehNames
from tests.bokeh_plotter_support.rendering import select_one_by_type


if TYPE_CHECKING:
    from bokeh.models.css import InlineStyleSheet
    from bokeh.plotting._figure import figure as figure_model


def assert_toolbar_tool_state(
    shown_plot: "figure_model",
    tap_tool: bokeh_models.TapTool,
    wheel_zoom_tool: bokeh_models.WheelZoomTool,
) -> None:
    assert tap_tool.visible is False
    assert (
        cast(
            "bokeh_models.HoverTool",
            select_one_by_type(shown_plot, bokeh_models.HoverTool),
        ).visible
        is False
    )
    assert wheel_zoom_tool.visible is False
    assert wheel_zoom_tool.speed == pytest.approx(1 / BokehNames.wheel_speed_denominator)
    assert shown_plot.toolbar.active_scroll == "auto"


def assert_primary_tool_counts(tool_type_names: list[str]) -> None:
    assert tool_type_names.count("PanTool") == 1
    assert tool_type_names.count("WheelZoomTool") == 1
    assert tool_type_names.count("ZoomInTool") == 1
    assert tool_type_names.count("ZoomOutTool") == 1
    assert tool_type_names.count("BoxZoomTool") == 1


def assert_secondary_tool_counts(tool_type_names: list[str]) -> None:
    assert tool_type_names.count("ResetTool") == 1
    assert tool_type_names.count("SaveTool") == 1
    assert tool_type_names.count("TapTool") == 1
    assert tool_type_names.count("HoverTool") == 1


def assert_toolbar_layout(plot: "figure_model") -> None:
    assert plot.output_backend == "canvas"
    assert plot.toolbar_location == "left"
    assert plot.toolbar_inner is True
    assert plot.toolbar_sticky is True
    assert plot.toolbar.logo is None


def assert_toolbar_styles(plot: "figure_model", stylesheet: "InlineStyleSheet") -> None:
    assert plot.toolbar.autohide is False
    assert plot.toolbar.stylesheets is not None
    assert len(plot.toolbar.stylesheets) == 1
    assert "position: fixed" in stylesheet.css
    assert "left: 16px" in stylesheet.css


def assert_large_graph_edge_contract(shown_plot: "figure_model") -> None:
    assert shown_plot.output_backend == "canvas"
    assert shown_plot.lod_threshold == 1
    assert select_one_by_type(shown_plot, Arrow) is None
    assert select_one_by_type(shown_plot, bokeh_models.PanTool) is not None
    assert type(shown_plot.toolbar.active_drag).__name__ == "PanTool"
