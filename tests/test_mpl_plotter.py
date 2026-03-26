import matplotlib.pyplot as plt
import networkx as nx
import pytest
from _pytest.monkeypatch import MonkeyPatch

from netimport_lib.visualizer import mpl_plotter


def _build_sample_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node("main.py", label="main.py", type="project_file")
    graph.add_node("os", label="os", type="std_lib")
    graph.add_node("requests", label="requests", type="external_lib")
    graph.add_edge("main.py", "os")
    graph.add_edge("main.py", "requests")

    return graph


def _build_non_planar_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    left_partition = ("a", "b", "c")
    right_partition = ("x", "y", "z")

    for left_node in left_partition:
        for right_node in right_partition:
            graph.add_edge(left_node, right_node)

    return graph


def test_prepare_mpl_render_builds_expected_visual_data() -> None:
    graph = _build_sample_graph()

    first_render = mpl_plotter.prepare_mpl_render(graph, "spring")
    second_render = mpl_plotter.prepare_mpl_render(graph, "spring")

    assert first_render.positions == second_render.positions
    assert first_render.ordered_node_ids == ("main.py", "os", "requests")
    assert first_render.node_sizes == (
        mpl_plotter.MIN_NODE_SIZE,
        mpl_plotter.MIN_NODE_SIZE + 2000,
        mpl_plotter.MIN_NODE_SIZE + 2000,
    )
    assert first_render.node_colors == (
        mpl_plotter.NODE_COLOR_MAP["project_file"],
        mpl_plotter.NODE_COLOR_MAP["std_lib"],
        mpl_plotter.NODE_COLOR_MAP["external_lib"],
    )
    assert first_render.node_labels == {
        "main.py": "main.py",
        "os": "os",
        "requests": "requests",
    }
    assert set(first_render.positions) == set(graph.nodes())
    assert all(
        isinstance(x_coord, float) and isinstance(y_coord, float)
        for x_coord, y_coord in first_render.positions.values()
    )


def test_prepare_mpl_render_rejects_unsupported_layout() -> None:
    graph = _build_sample_graph()

    with pytest.raises(ValueError, match="Unsupported Matplotlib layout 'grid'"):
        mpl_plotter.prepare_mpl_render(graph, "grid")


@pytest.mark.parametrize("layout", ("spring", "circular", "shell", "planar_layout"))
def test_prepare_mpl_render_supports_each_registered_layout(layout: str) -> None:
    graph = _build_sample_graph()

    render_data = mpl_plotter.prepare_mpl_render(graph, layout)

    assert set(render_data.positions) == set(graph.nodes())


def test_prepare_mpl_render_rejects_non_planar_graph_for_planar_layout() -> None:
    graph = _build_non_planar_graph()

    with pytest.raises(
        ValueError,
        match="Matplotlib layout 'planar_layout' requires a planar graph.",
    ):
        mpl_plotter.prepare_mpl_render(graph, "planar_layout")


def test_draw_graph_mpl_smoke_headless(monkeypatch: MonkeyPatch) -> None:
    graph = _build_sample_graph()
    shown: list[str] = []

    plt.switch_backend("Agg")
    monkeypatch.setattr(plt, "show", lambda: shown.append("show"))

    mpl_plotter.draw_graph_mpl(graph, "spring")

    assert shown == ["show"]
    plt.close("all")


def test_draw_graph_mpl_does_not_mutate_input_graph(monkeypatch: MonkeyPatch) -> None:
    graph = _build_sample_graph()
    before_node_data = {
        node_id: dict(node_data) for node_id, node_data in graph.nodes(data=True)
    }

    plt.switch_backend("Agg")
    monkeypatch.setattr(plt, "show", lambda: None)

    mpl_plotter.draw_graph_mpl(graph, "shell")

    after_node_data = {
        node_id: dict(node_data) for node_id, node_data in graph.nodes(data=True)
    }
    assert after_node_data == before_node_data
    plt.close("all")
