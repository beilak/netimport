"""Shared constants for the Bokeh visualizer."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

from netimport_lib.visualizer.bokeh_plotter_render_models import EdgeVisualStyle


@dataclass(frozen=True, slots=True)
class _BokehPlotterConstants:
    freeze_random_seed: int
    label_padding: float
    min_node_size: int
    medium_graph_min_node_size: int
    compact_graph_min_node_size: int
    max_node_size: int
    medium_graph_max_node_size: int
    compact_graph_max_node_size: int
    node_size_sqrt_scale: float
    medium_graph_node_size_sqrt_scale: float
    compact_graph_node_size_sqrt_scale: float
    medium_graph_node_count_threshold: int
    compact_graph_node_count_threshold: int
    medium_edge_count_threshold: int
    compact_edge_count_threshold: int
    arrow_render_node_threshold: int
    arrow_render_edge_threshold: int
    lod_render_node_threshold: int
    lod_render_edge_threshold: int
    lod_factor: int
    lod_interval_ms: int
    lod_timeout_ms: int
    initial_view_padding_fraction: float
    initial_view_min_padding_units: float
    initial_view_safety_scale: float
    min_node_block_span: float
    node_block_cell_span: float
    node_layout_inset: float
    node_layout_clearance_units: float
    node_layout_outer_padding_units: float
    layout_viewport_padding_units: float
    folder_padding_x: float
    folder_padding_y: float
    folder_label_height: float
    folder_section_gap: float
    folder_grid_gap_x: float
    folder_grid_gap_y: float
    root_section_gap: float
    min_folder_content_width: float
    min_folder_content_height: float
    default_node_layout_k: float
    base_plot_width: int
    base_plot_height: int
    max_plot_width: int
    max_plot_height: int
    plot_pixels_per_layout_unit: float
    toolbar_button_width_px: int
    toolbar_button_height_px: int
    toolbar_icon_scale_percent: int
    toolbar_viewport_left_px: int
    toolbar_viewport_top_px: int
    color_map: dict[str, str]
    default_node_color: str
    bokeh_output_prefix: str
    bokeh_output_suffix: str
    bokeh_plot_title: str
    interactive_plot_title: str
    skipped_auto_open_controller_names: frozenset[str]
    zero_float: int
    half_divisor: float
    spring_layout_iterations: int
    layout_density_divisor: float
    layout_folder_scale_limit: float
    layout_folder_divisor: float
    layout_gap_scale_factor: float
    layout_padding_scale_factor: float
    layout_inset_scale_factor: float
    side_by_side_area_threshold: float
    empty_plot_range_extent: float
    min_plot_aspect_ratio: float
    folder_rect_fill_color: str
    black_color: str
    folder_rect_fill_alpha: float
    node_fill_alpha: float
    edge_hover_line_alpha: float
    edge_selection_line_alpha: float
    compact_edge_line_alpha: float
    compact_edge_line_width: float
    compact_arrow_alpha: float
    medium_edge_line_alpha: float
    medium_arrow_alpha: float
    medium_arrow_line_width: float
    default_edge_line_alpha: float
    default_edge_line_width: float
    default_arrow_alpha: float
    default_arrow_line_width: float
    folder_x_field: str
    folder_y_field: str
    folder_label_y_field: str
    folder_width_field: str
    folder_height_field: str
    folder_name_field: str
    folder_color_field: str
    viz_size_field: str
    layout_position_padding_multiplier: float
    plot_node_complexity_threshold: int
    plot_folder_complexity_threshold: int
    plot_width_node_step: int
    plot_width_folder_step: int
    plot_height_node_step: int
    plot_height_folder_step: int
    plot_width_node_size_step: int
    plot_height_node_size_step: int
    compact_edge_style: EdgeVisualStyle
    medium_edge_style: EdgeVisualStyle
    default_edge_style: EdgeVisualStyle


def _load_constants_payload() -> dict[str, Any]:
    constants_path = Path(__file__).with_name("bokeh_plotter_constants.json")
    return cast("dict[str, Any]", json.loads(constants_path.read_text(encoding="utf-8")))


def _build_edge_style(raw_style: object) -> EdgeVisualStyle:
    style_data = cast("dict[str, Any]", raw_style)
    return EdgeVisualStyle(
        line_alpha=float(style_data["line_alpha"]),
        line_width=float(style_data["line_width"]),
        arrow_alpha=float(style_data["arrow_alpha"]),
        arrow_line_width=float(style_data["arrow_line_width"]),
        arrow_head_size=int(style_data["arrow_head_size"]),
    )


def _build_constants() -> _BokehPlotterConstants:
    raw_constants = _load_constants_payload()
    return _BokehPlotterConstants(
        **cast(
            "Any",
            {
                **raw_constants,
                "color_map": cast("dict[str, str]", raw_constants["color_map"]),
                "skipped_auto_open_controller_names": frozenset(
                    cast("list[str]", raw_constants["skipped_auto_open_controller_names"]),
                ),
                "compact_edge_style": _build_edge_style(raw_constants["compact_edge_style"]),
                "medium_edge_style": _build_edge_style(raw_constants["medium_edge_style"]),
                "default_edge_style": _build_edge_style(raw_constants["default_edge_style"]),
            },
        ),
    )


CONSTANTS: Final[_BokehPlotterConstants] = _build_constants()
