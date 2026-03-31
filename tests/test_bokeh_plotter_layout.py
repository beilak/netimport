from netimport_lib.visualizer import bokeh_plotter
from tests.bokeh_plotter_support.bounds import (
    folder_rect,
    rect_width_per_node_scale,
    rects_overlap,
)
from tests.bokeh_plotter_support.geometry import node_visual_size, point_is_inside_rect
from tests.bokeh_plotter_support.graphs import (
    build_hub_graph,
    build_sibling_folder_graph,
    build_single_folder_graph,
)
from tests.bokeh_plotter_support.names import BokehNames
from tests.bokeh_plotter_support.plot_assertions import assert_nodes_fit_folder


def test_nodes_stay_inside_folder_boxes() -> None:
    render_data = bokeh_plotter.prepare_bokeh_render(
        build_sibling_folder_graph(),
        BokehNames.constrained_layout,
    )
    alpha_rect = folder_rect(render_data, BokehNames.alpha_folder)
    beta_rect = folder_rect(render_data, BokehNames.beta_folder)

    assert_nodes_fit_folder(
        render_data,
        (BokehNames.alpha_a_file, BokehNames.alpha_b_file),
        alpha_rect,
        beta_rect,
    )
    assert_nodes_fit_folder(
        render_data,
        (BokehNames.beta_c_file, BokehNames.beta_d_file),
        beta_rect,
        alpha_rect,
    )
    assert not point_is_inside_rect(*render_data.final_positions[BokehNames.root_file], alpha_rect)
    assert not point_is_inside_rect(*render_data.final_positions[BokehNames.root_file], beta_rect)


def test_sibling_folder_boxes_do_not_overlap() -> None:
    render_data = bokeh_plotter.prepare_bokeh_render(
        build_sibling_folder_graph(),
        BokehNames.constrained_layout,
    )

    assert not rects_overlap(
        folder_rect(render_data, BokehNames.alpha_folder),
        folder_rect(render_data, BokehNames.beta_folder),
    )


def test_large_graph_expands_folder_geometry() -> None:
    small_rect = folder_rect(
        bokeh_plotter.prepare_bokeh_render(
            build_single_folder_graph(4),
            BokehNames.constrained_layout,
        ),
        BokehNames.pkg_folder,
    )
    large_rect = folder_rect(
        bokeh_plotter.prepare_bokeh_render(
            build_single_folder_graph(BokehNames.large_graph_node_count),
            BokehNames.constrained_layout,
        ),
        BokehNames.pkg_folder,
    )

    assert rect_width_per_node_scale(
        large_rect,
        BokehNames.large_graph_node_count,
    ) > rect_width_per_node_scale(small_rect, 4)


def test_caps_high_degree_nodes() -> None:
    render_data = bokeh_plotter.prepare_bokeh_render(
        build_hub_graph(BokehNames.high_degree_leaf_count),
        BokehNames.constrained_layout,
    )
    hub_visual_data = render_data.node_visual_data[BokehNames.pkg_hub_file]

    assert hub_visual_data["viz_degree"] == BokehNames.expected_hub_degree
    assert node_visual_size(render_data, BokehNames.pkg_hub_file) <= bokeh_plotter.MAX_NODE_SIZE
    assert node_visual_size(render_data, BokehNames.pkg_hub_file) > bokeh_plotter.MIN_NODE_SIZE
