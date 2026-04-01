from netimport_lib.visualizer.bokeh_plotter_public_constants_a import (
    ARROW_RENDER_EDGE_THRESHOLD,
    BASE_PLOT_HEIGHT,
    HALF_DIVISOR,
    MAX_NODE_SIZE,
)
from netimport_lib.visualizer.bokeh_plotter_public_constants_b import (
    MEDIUM_GRAPH_MIN_NODE_SIZE,
    MEDIUM_GRAPH_NODE_COUNT_THRESHOLD,
    MIN_NODE_SIZE,
    VIZ_SIZE_FIELD,
    ZERO_FLOAT,
)


class BokehNames:
    root_file = "root.py"
    project_file_type = "project_file"
    unresolved_type = "unresolved"
    pkg_folder = "pkg"
    pkg_sub_folder = "pkg/sub"
    alpha_folder = "alpha"
    beta_folder = "beta"
    pkg_a_file = "pkg/a.py"
    pkg_sub_b_file = "pkg/sub/b.py"
    alpha_a_file = "alpha/a.py"
    alpha_b_file = "alpha/b.py"
    beta_c_file = "beta/c.py"
    beta_d_file = "beta/d.py"
    pkg_hub_file = "pkg/hub.py"
    b_file_label = "b.py"
    constrained_layout = "constrained"
    utf8 = "utf-8"
    type_query_key = "type"
    present_plot_attr = "_present_plot"
    save_plot_attr = "_save_plot"
    open_saved_plot_attr = "_open_saved_plot"
    get_browser_controller_attr = "get_browser_controller"
    viz_size_field = VIZ_SIZE_FIELD
    half_divisor = HALF_DIVISOR
    zero_float = ZERO_FLOAT
    large_graph_node_count = MEDIUM_GRAPH_NODE_COUNT_THRESHOLD // 5
    high_degree_leaf_count = MAX_NODE_SIZE - MIN_NODE_SIZE
    expected_hub_degree = high_degree_leaf_count + 1
    chain_comparison_node_count = MEDIUM_GRAPH_NODE_COUNT_THRESHOLD // 6
    hub_comparison_leaf_count = chain_comparison_node_count - 1
    range_coverage_leaf_count = ARROW_RENDER_EDGE_THRESHOLD // 8 + 1
    light_edge_leaf_count = ARROW_RENDER_EDGE_THRESHOLD
    wheel_speed_denominator = BASE_PLOT_HEIGHT - MEDIUM_GRAPH_MIN_NODE_SIZE * 10
