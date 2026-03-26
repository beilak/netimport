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


def test_draw_graph_mpl_smoke_headless(monkeypatch: MonkeyPatch) -> None:
    graph = _build_sample_graph()
    shown: list[str] = []

    plt.switch_backend("Agg")
    monkeypatch.setattr(plt, "show", lambda: shown.append("show"))

    mpl_plotter.draw_graph_mpl(graph, "spring")

    assert shown == ["show"]
    plt.close("all")
