import networkx as nx
import pytest

from netimport_lib.visualizer import bokeh_plotter
from netimport_lib.visualizer.bokeh_plotter_public_constants_a import COLOR_MAP
from tests.bokeh_plotter_support.graphs import build_sample_graph
from tests.bokeh_plotter_support.names import BokehNames


def test_prepare_render_visual_data() -> None:
    graph = build_sample_graph()

    render_data = bokeh_plotter.prepare_bokeh_render(graph, BokehNames.constrained_layout)

    assert set(render_data.final_positions) == set(graph.nodes())
    assert set(render_data.folder_rect_data["name"]) == {"pkg", "sub"}
    assert (
        len(render_data.folder_rect_data["x"]),
        len(render_data.arrow_source_data["start_x"]),
        len(render_data.arrow_source_data["end_x"]),
    ) == (2, graph.number_of_edges(), graph.number_of_edges())
    assert render_data.node_visual_data[BokehNames.pkg_sub_b_file] == {
        "viz_size": 26,
        "viz_color": COLOR_MAP[BokehNames.unresolved_type],
        "viz_label": BokehNames.b_file_label,
        "viz_degree": 1,
        "viz_type": BokehNames.unresolved_type,
        "viz_label_y_offset": 33,
        "in_degree": 1,
        "out_degree": 0,
        "total_degree": 1,
    }


def test_reject_unsupported_layout() -> None:
    with pytest.raises(ValueError, match="Unsupported Bokeh layout 'spring'"):
        bokeh_plotter.prepare_bokeh_render(build_sample_graph(), "spring")


def test_prepare_bokeh_render_handles_empty_graph() -> None:
    render_data = bokeh_plotter.prepare_bokeh_render(nx.DiGraph(), BokehNames.constrained_layout)

    assert render_data.final_positions == {}
    assert render_data.folder_rect_data == {
        "x": [],
        "y": [],
        "label_y": [],
        "width": [],
        "height": [],
        "name": [],
        "color": [],
    }
    assert render_data.arrow_source_data == {
        "start_x": [],
        "start_y": [],
        "end_x": [],
        "end_y": [],
    }
    assert render_data.node_visual_data == {}


def test_prepare_render_is_deterministic() -> None:
    first_graph = build_sample_graph()
    second_graph = nx.DiGraph()
    second_graph.add_node(
        BokehNames.pkg_sub_b_file,
        label="b.py",
        folder=BokehNames.pkg_sub_folder,
        type=BokehNames.unresolved_type,
        in_degree=1,
        out_degree=0,
        total_degree=1,
    )
    second_graph.add_node(
        BokehNames.pkg_a_file,
        label="a.py",
        folder=BokehNames.pkg_folder,
        type=BokehNames.project_file_type,
        in_degree=1,
        out_degree=1,
        total_degree=2,
    )
    second_graph.add_node(
        BokehNames.root_file,
        label=BokehNames.root_file,
        folder="",
        is_root_folder=True,
        type=BokehNames.project_file_type,
        in_degree=0,
        out_degree=1,
        total_degree=1,
    )
    second_graph.add_edge(BokehNames.pkg_a_file, BokehNames.pkg_sub_b_file)
    second_graph.add_edge(BokehNames.root_file, BokehNames.pkg_a_file)

    first_render = bokeh_plotter.prepare_bokeh_render(first_graph, BokehNames.constrained_layout)
    second_render = bokeh_plotter.prepare_bokeh_render(second_graph, BokehNames.constrained_layout)

    assert first_render.final_positions == second_render.final_positions
    assert first_render.folder_rect_data == second_render.folder_rect_data
    assert first_render.arrow_source_data == second_render.arrow_source_data
