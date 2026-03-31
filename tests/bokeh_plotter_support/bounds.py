import math

from netimport_lib.visualizer import bokeh_plotter
from tests.bokeh_plotter_support.geometry import (
    build_rect_map,
    node_bounds,
    rect_bounds,
)
from tests.bokeh_plotter_support.rendering import half


def merge_bounds(
    current_bounds: tuple[float | None, ...],
    candidate_bounds: tuple[float, float, float, float],
) -> tuple[float | None, ...]:
    return (
        candidate_bounds[0]
        if current_bounds[0] is None
        else min(current_bounds[0], candidate_bounds[0]),
        candidate_bounds[1]
        if current_bounds[1] is None
        else max(current_bounds[1], candidate_bounds[1]),
        candidate_bounds[2]
        if current_bounds[2] is None
        else min(current_bounds[2], candidate_bounds[2]),
        candidate_bounds[3]
        if current_bounds[3] is None
        else max(current_bounds[3], candidate_bounds[3]),
    )


def normalize_bounds(
    bounds: tuple[float | None, ...],
) -> tuple[float, float, float, float]:
    return (
        bokeh_plotter.ZERO_FLOAT if bounds[0] is None else bounds[0],
        bokeh_plotter.ZERO_FLOAT if bounds[1] is None else bounds[1],
        bokeh_plotter.ZERO_FLOAT if bounds[2] is None else bounds[2],
        bokeh_plotter.ZERO_FLOAT if bounds[3] is None else bounds[3],
    )


def build_render_bounds(
    render_data: bokeh_plotter.PreparedBokehRender,
) -> tuple[float, float, float, float]:
    bounds: tuple[float | None, ...] = (
        None,
        None,
        None,
        None,
    )
    for node_id, position in render_data.final_positions.items():
        bounds = merge_bounds(bounds, node_bounds(render_data, node_id, position))
    for rect in build_rect_map(render_data.folder_rect_data).values():
        bounds = merge_bounds(bounds, rect_bounds(rect))
    return normalize_bounds(bounds)


def axis_overlap(
    first_center: float,
    second_center: float,
    first_size: float,
    second_size: float,
) -> bool:
    return abs(first_center - second_center) < half(first_size + second_size)


def rects_overlap(
    first_rect: tuple[float, float, float, float],
    second_rect: tuple[float, float, float, float],
) -> bool:
    horizontal_overlap = axis_overlap(
        first_rect[0],
        second_rect[0],
        first_rect[2],
        second_rect[2],
    )
    vertical_overlap = axis_overlap(
        first_rect[1],
        second_rect[1],
        first_rect[3],
        second_rect[3],
    )
    return horizontal_overlap and vertical_overlap


def rect_width_per_node_scale(rect: tuple[float, float, float, float], node_count: int) -> float:
    return rect[2] / math.sqrt(node_count)


def folder_rect(
    render_data: bokeh_plotter.PreparedBokehRender,
    folder_name: str,
) -> tuple[float, float, float, float]:
    return build_rect_map(render_data.folder_rect_data)[folder_name]
