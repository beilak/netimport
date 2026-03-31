from typing import TYPE_CHECKING, cast

from bokeh import models as bokeh_models

from netimport_lib.visualizer import bokeh_plotter
from tests.bokeh_plotter_support.bounds import build_render_bounds
from tests.bokeh_plotter_support.geometry import node_visual_fits_inside_rect, point_is_inside_rect


if TYPE_CHECKING:
    from bokeh.plotting._figure import figure as figure_model


def assert_nodes_fit_folder(
    render_data: bokeh_plotter.PreparedBokehRender,
    node_ids: tuple[str, ...],
    own_rect: tuple[float, float, float, float],
    other_rect: tuple[float, float, float, float],
) -> None:
    for node_id in node_ids:
        node_x, node_y = render_data.final_positions[node_id]
        assert point_is_inside_rect(node_x, node_y, own_rect)
        assert not point_is_inside_rect(node_x, node_y, other_rect)
        assert node_visual_fits_inside_rect(node_id, render_data, own_rect)


def assert_range_covers(range_value: bokeh_models.Range1d, minimum: float, maximum: float) -> None:
    assert isinstance(range_value.start, float)
    assert isinstance(range_value.end, float)
    assert range_value.start <= minimum
    assert range_value.end >= maximum


def plot_dimensions(plot: "figure_model") -> tuple[int, int]:
    assert plot.width is not None
    assert plot.height is not None
    return plot.width, plot.height


def assert_plot_covers_bounds(
    plot: "figure_model",
    bounds: tuple[float, float, float, float],
) -> None:
    assert isinstance(plot.x_range, bokeh_models.Range1d)
    assert isinstance(plot.y_range, bokeh_models.Range1d)
    assert plot.match_aspect is True
    assert_range_covers(plot.x_range, bounds[0], bounds[1])
    assert_range_covers(plot.y_range, bounds[2], bounds[3])


def assert_render_covers_bounds(
    plot: "figure_model",
    render_data: bokeh_plotter.PreparedBokehRender,
) -> None:
    assert_plot_covers_bounds(plot, build_render_bounds(render_data))


def hover_tool_for(plot: "figure_model") -> bokeh_models.HoverTool:
    return cast("bokeh_models.HoverTool", plot.select_one({"type": bokeh_models.HoverTool}))

