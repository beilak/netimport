from netimport_lib.visualizer import bokeh_plotter


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
    viz_size_field = bokeh_plotter.VIZ_SIZE_FIELD
    half_divisor = bokeh_plotter.HALF_DIVISOR
    zero_float = bokeh_plotter.ZERO_FLOAT
    large_graph_node_count = bokeh_plotter.MEDIUM_GRAPH_NODE_COUNT_THRESHOLD // 5
    high_degree_leaf_count = bokeh_plotter.MAX_NODE_SIZE - bokeh_plotter.MIN_NODE_SIZE
    expected_hub_degree = high_degree_leaf_count + 1
    chain_comparison_node_count = bokeh_plotter.MEDIUM_GRAPH_NODE_COUNT_THRESHOLD // 6
    hub_comparison_leaf_count = chain_comparison_node_count - 1
    range_coverage_leaf_count = bokeh_plotter.ARROW_RENDER_EDGE_THRESHOLD // 8 + 1
    light_edge_leaf_count = bokeh_plotter.ARROW_RENDER_EDGE_THRESHOLD
    wheel_speed_denominator = (
        bokeh_plotter.BASE_PLOT_HEIGHT - bokeh_plotter.MEDIUM_GRAPH_MIN_NODE_SIZE * 10
    )

