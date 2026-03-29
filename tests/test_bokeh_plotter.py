import math
from pathlib import Path
from typing import TYPE_CHECKING, cast

import networkx as nx
import pytest
from _pytest.monkeypatch import MonkeyPatch
from bokeh.models import HoverTool, PointDrawTool
from bokeh.models.annotations import Arrow
from bokeh.models.renderers import GraphRenderer

from netimport_lib.visualizer import bokeh_plotter


if TYPE_CHECKING:
    from bokeh.plotting._figure import figure as figure_model

    from netimport_lib.visualizer.bokeh_plotter import FolderRectData


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


def _build_sibling_folder_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node(
        "root.py",
        label="root.py",
        folder="",
        is_root_folder=True,
        type="project_file",
        in_degree=0,
        out_degree=2,
        total_degree=2,
    )
    graph.add_node(
        "alpha/a.py",
        label="a.py",
        folder="alpha",
        type="project_file",
        in_degree=1,
        out_degree=1,
        total_degree=2,
    )
    graph.add_node(
        "alpha/b.py",
        label="b.py",
        folder="alpha",
        type="project_file",
        in_degree=1,
        out_degree=1,
        total_degree=2,
    )
    graph.add_node(
        "beta/c.py",
        label="c.py",
        folder="beta",
        type="project_file",
        in_degree=2,
        out_degree=1,
        total_degree=3,
    )
    graph.add_node(
        "beta/d.py",
        label="d.py",
        folder="beta",
        type="project_file",
        in_degree=1,
        out_degree=0,
        total_degree=1,
    )
    graph.add_edge("root.py", "alpha/a.py")
    graph.add_edge("root.py", "beta/c.py")
    graph.add_edge("alpha/a.py", "alpha/b.py")
    graph.add_edge("alpha/b.py", "beta/c.py")
    graph.add_edge("beta/c.py", "beta/d.py")

    return graph


def _build_single_folder_graph(node_count: int) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node(
        "root.py",
        label="root.py",
        folder="",
        is_root_folder=True,
        type="project_file",
        in_degree=0,
        out_degree=1 if node_count > 0 else 0,
        total_degree=1 if node_count > 0 else 0,
    )
    previous_node_id = "root.py"
    for index in range(node_count):
        node_id = f"pkg/node_{index}.py"
        graph.add_node(
            node_id,
            label=f"node_{index}.py",
            folder="pkg",
            type="project_file",
            in_degree=1,
            out_degree=1 if index < node_count - 1 else 0,
            total_degree=2 if 0 < index < node_count - 1 else 1,
        )
        graph.add_edge(previous_node_id, node_id)
        previous_node_id = node_id

    return graph


def _build_rect_map(
    folder_rect_data: "FolderRectData",
) -> dict[str, tuple[float, float, float, float]]:
    return {
        name: (x_coord, y_coord, width, height)
        for name, x_coord, y_coord, width, height in zip(
            folder_rect_data["name"],
            folder_rect_data["x"],
            folder_rect_data["y"],
            folder_rect_data["width"],
            folder_rect_data["height"],
            strict=True,
        )
    }


def _point_is_inside_rect(
    x_coord: float,
    y_coord: float,
    rect: tuple[float, float, float, float],
) -> bool:
    rect_x, rect_y, rect_width, rect_height = rect
    return (
        abs(x_coord - rect_x) <= rect_width / 2.0
        and abs(y_coord - rect_y) <= rect_height / 2.0
    )


def _rects_overlap(
    first_rect: tuple[float, float, float, float],
    second_rect: tuple[float, float, float, float],
) -> bool:
    first_x, first_y, first_width, first_height = first_rect
    second_x, second_y, second_width, second_height = second_rect
    return (
        abs(first_x - second_x) < (first_width + second_width) / 2.0
        and abs(first_y - second_y) < (first_height + second_height) / 2.0
    )


def test_prepare_bokeh_render_builds_expected_visual_data() -> None:
    graph = _build_sample_graph()

    render_data = bokeh_plotter.prepare_bokeh_render(graph, "constrained")

    assert set(render_data.final_positions) == set(graph.nodes())
    assert set(render_data.folder_rect_data["name"]) == {"pkg", "sub"}
    assert len(render_data.folder_rect_data["x"]) == 2
    assert len(render_data.arrow_source_data["start_x"]) == graph.number_of_edges()
    assert len(render_data.arrow_source_data["end_x"]) == graph.number_of_edges()
    assert render_data.node_visual_data["pkg/sub/b.py"] == {
        "viz_size": bokeh_plotter.MIN_NODE_SIZE + 10,
        "viz_color": bokeh_plotter.COLOR_MAP["unresolved"],
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
        bokeh_plotter.prepare_bokeh_render(graph, "spring")


def test_prepare_bokeh_render_handles_empty_graph() -> None:
    graph = nx.DiGraph()

    render_data = bokeh_plotter.prepare_bokeh_render(graph, "constrained")

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


def test_draw_bokeh_graph_smoke_headless_without_mutating_input(
    monkeypatch: MonkeyPatch,
) -> None:
    graph = _build_sample_graph()
    shown_plots: list[object] = []

    monkeypatch.setattr(bokeh_plotter, "_present_plot", shown_plots.append)

    bokeh_plotter.draw_bokeh_graph(graph, "constrained")

    shown_plot = cast("figure_model", shown_plots[0])
    assert len(shown_plots) == 1
    assert len(shown_plot.select({"type": GraphRenderer})) == 1
    assert "viz_size" not in graph.nodes["pkg/a.py"]


def test_draw_bokeh_graph_configures_headless_plot_contract(
    monkeypatch: MonkeyPatch,
) -> None:
    graph = _build_sample_graph()
    shown_plots: list[object] = []

    monkeypatch.setattr(bokeh_plotter, "_present_plot", shown_plots.append)

    bokeh_plotter.draw_bokeh_graph(graph, "constrained")

    shown_plot = cast("figure_model", shown_plots[0])
    hover_tool = cast("HoverTool", shown_plot.select_one({"type": HoverTool}))
    drag_tool = cast("PointDrawTool", shown_plot.select_one({"type": PointDrawTool}))

    assert hover_tool.tooltips == [
        ("Name", "@viz_label"),
        ("Type", "@viz_type"),
        ("Total Links", "@total_degree"),
        ("Incoming", "@in_degree"),
        ("Outgoing", "@out_degree"),
        ("ID", "@index"),
        ("Folder", "@folder"),
    ]
    assert hover_tool.renderers is not None
    assert len(hover_tool.renderers) == 1
    assert drag_tool.renderers is not None
    assert len(drag_tool.renderers) == 1
    assert len(shown_plot.select({"type": Arrow})) == 1


def test_present_plot_returns_manual_open_message_when_auto_open_is_skipped(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "netimport-graph.html"

    monkeypatch.setattr(bokeh_plotter, "_save_plot", lambda _plot: output_path)
    monkeypatch.setattr(bokeh_plotter, "_open_saved_plot", lambda _path: False)

    message = bokeh_plotter.draw_bokeh_graph(_build_sample_graph(), "constrained")

    assert message == (
        "Interactive dependency graph saved to "
        f"{output_path}. Automatic browser launch is unavailable in this environment; "
        "open the file manually."
    )


def test_draw_bokeh_graph_returns_no_message_when_auto_open_succeeds(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "netimport-graph.html"

    monkeypatch.setattr(bokeh_plotter, "_save_plot", lambda _plot: output_path)
    monkeypatch.setattr(bokeh_plotter, "_open_saved_plot", lambda _path: True)

    message = bokeh_plotter.draw_bokeh_graph(_build_sample_graph(), "constrained")

    assert message is None


def test_prepare_bokeh_render_is_deterministic_for_equivalent_graph_orders() -> None:
    first_graph = _build_sample_graph()
    second_graph = nx.DiGraph()
    second_graph.add_node(
        "pkg/sub/b.py",
        label="b.py",
        folder="pkg/sub",
        type="unresolved",
        in_degree=1,
        out_degree=0,
        total_degree=1,
    )
    second_graph.add_node(
        "pkg/a.py",
        label="a.py",
        folder="pkg",
        type="project_file",
        in_degree=1,
        out_degree=1,
        total_degree=2,
    )
    second_graph.add_node(
        "root.py",
        label="root.py",
        folder="",
        is_root_folder=True,
        type="project_file",
        in_degree=0,
        out_degree=1,
        total_degree=1,
    )
    second_graph.add_edge("pkg/a.py", "pkg/sub/b.py")
    second_graph.add_edge("root.py", "pkg/a.py")

    first_render = bokeh_plotter.prepare_bokeh_render(first_graph, "constrained")
    second_render = bokeh_plotter.prepare_bokeh_render(second_graph, "constrained")

    assert first_render.final_positions == second_render.final_positions
    assert first_render.folder_rect_data == second_render.folder_rect_data
    assert first_render.arrow_source_data == second_render.arrow_source_data


def test_prepare_bokeh_render_keeps_nodes_inside_their_own_folder_boxes() -> None:
    graph = _build_sibling_folder_graph()

    render_data = bokeh_plotter.prepare_bokeh_render(graph, "constrained")
    rect_map = _build_rect_map(render_data.folder_rect_data)
    alpha_rect = rect_map["alpha"]
    beta_rect = rect_map["beta"]

    for node_id in ("alpha/a.py", "alpha/b.py"):
        node_x, node_y = render_data.final_positions[node_id]
        assert _point_is_inside_rect(node_x, node_y, alpha_rect)
        assert not _point_is_inside_rect(node_x, node_y, beta_rect)

    for node_id in ("beta/c.py", "beta/d.py"):
        node_x, node_y = render_data.final_positions[node_id]
        assert _point_is_inside_rect(node_x, node_y, beta_rect)
        assert not _point_is_inside_rect(node_x, node_y, alpha_rect)

    root_x, root_y = render_data.final_positions["root.py"]
    assert not _point_is_inside_rect(root_x, root_y, alpha_rect)
    assert not _point_is_inside_rect(root_x, root_y, beta_rect)


def test_prepare_bokeh_render_separates_sibling_folder_boxes() -> None:
    graph = _build_sibling_folder_graph()

    render_data = bokeh_plotter.prepare_bokeh_render(graph, "constrained")
    rect_map = _build_rect_map(render_data.folder_rect_data)

    assert not _rects_overlap(rect_map["alpha"], rect_map["beta"])


def test_prepare_bokeh_render_expands_single_folder_geometry_for_large_graphs() -> None:
    small_graph = _build_single_folder_graph(4)
    large_graph = _build_single_folder_graph(16)
    small_render = bokeh_plotter.prepare_bokeh_render(small_graph, "constrained")
    large_render = bokeh_plotter.prepare_bokeh_render(large_graph, "constrained")
    small_rect = _build_rect_map(small_render.folder_rect_data)["pkg"]
    large_rect = _build_rect_map(large_render.folder_rect_data)["pkg"]

    assert large_rect[2] / math.sqrt(16) > small_rect[2] / math.sqrt(4)


def test_draw_bokeh_graph_uses_larger_canvas_for_large_graphs(
    monkeypatch: MonkeyPatch,
) -> None:
    shown_plots: list[object] = []

    monkeypatch.setattr(bokeh_plotter, "_present_plot", shown_plots.append)

    bokeh_plotter.draw_bokeh_graph(_build_single_folder_graph(4), "constrained")
    bokeh_plotter.draw_bokeh_graph(_build_single_folder_graph(16), "constrained")

    small_plot = cast("figure_model", shown_plots[0])
    large_plot = cast("figure_model", shown_plots[1])

    assert large_plot.width is not None
    assert small_plot.width is not None
    assert large_plot.height is not None
    assert small_plot.height is not None
    assert large_plot.width > small_plot.width
    assert large_plot.height > small_plot.height
