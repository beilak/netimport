from typing import TYPE_CHECKING, cast

import networkx as nx
import pytest
from _pytest.monkeypatch import MonkeyPatch
from bokeh.models.renderers import GraphRenderer

from netimport_lib.visualizer import bokeh_plotter_v2


if TYPE_CHECKING:
    from bokeh.plotting._figure import figure as figure_model


def _build_sample_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node(
        "root.py",
        label="root.py",
        folder="",
        is_root_folder=True,
        type="project_file",
        in_degree=0,
        out_degree=1,
        total_degree=1,
    )
    graph.add_node(
        "pkg/a.py",
        label="a.py",
        folder="pkg",
        type="project_file",
        in_degree=1,
        out_degree=1,
        total_degree=2,
    )
    graph.add_node(
        "pkg/sub/b.py",
        label="b.py",
        folder="pkg/sub",
        type="unresolved",
        in_degree=1,
        out_degree=0,
        total_degree=1,
    )
    graph.add_edge("root.py", "pkg/a.py")
    graph.add_edge("pkg/a.py", "pkg/sub/b.py")

    return graph


def test_prepare_bokeh_render_builds_expected_visual_data() -> None:
    graph = _build_sample_graph()

    render_data = bokeh_plotter_v2.prepare_bokeh_render(graph, "constrained")

    assert set(render_data.final_positions) == set(graph.nodes())
    assert set(render_data.folder_rect_data["name"]) == {"pkg", "sub"}
    assert len(render_data.folder_rect_data["x"]) == 2
    assert len(render_data.arrow_source_data["start_x"]) == graph.number_of_edges()
    assert len(render_data.arrow_source_data["end_x"]) == graph.number_of_edges()
    assert render_data.node_visual_data["pkg/sub/b.py"] == {
        "viz_size": bokeh_plotter_v2.MIN_NODE_SIZE + 10,
        "viz_color": bokeh_plotter_v2.COLOR_MAP["unresolved"],
        "viz_label": "b.py",
        "viz_degree": 1,
        "viz_type": "unresolved",
        "viz_label_y_offset": 35,
        "in_degree": 1,
        "out_degree": 0,
        "total_degree": 1,
    }


def test_prepare_bokeh_render_rejects_unsupported_layout() -> None:
    graph = _build_sample_graph()

    with pytest.raises(ValueError, match="Unsupported Bokeh layout 'spring'"):
        bokeh_plotter_v2.prepare_bokeh_render(graph, "spring")


def test_draw_bokeh_graph_smoke_headless_without_mutating_input(
    monkeypatch: MonkeyPatch,
) -> None:
    graph = _build_sample_graph()
    shown_plots: list[object] = []

    monkeypatch.setattr(bokeh_plotter_v2, "show", lambda plot: shown_plots.append(plot))

    bokeh_plotter_v2.draw_bokeh_graph(graph, "constrained")

    shown_plot = cast("figure_model", shown_plots[0])
    assert len(shown_plots) == 1
    assert len(shown_plot.select({"type": GraphRenderer})) == 1
    assert "viz_size" not in graph.nodes["pkg/a.py"]
