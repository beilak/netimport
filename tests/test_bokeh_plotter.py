import math
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING, cast

import networkx as nx
import pytest
from _pytest.monkeypatch import MonkeyPatch
from bokeh.models import HoverTool, PanTool, Range1d, TapTool, WheelZoomTool
from bokeh.models.annotations import Arrow
from bokeh.models.renderers import GraphRenderer

from netimport_lib.visualizer import bokeh_plotter


if TYPE_CHECKING:
    from bokeh.models.css import InlineStyleSheet
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


def _build_hub_graph(leaf_count: int) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node(
        "root.py",
        label="root.py",
        folder="",
        is_root_folder=True,
        type="project_file",
        in_degree=0,
        out_degree=1 if leaf_count > 0 else 0,
        total_degree=1 if leaf_count > 0 else 0,
    )
    graph.add_node(
        "pkg/hub.py",
        label="hub.py",
        folder="pkg",
        type="project_file",
        in_degree=1 if leaf_count > 0 else 0,
        out_degree=leaf_count,
        total_degree=leaf_count + (1 if leaf_count > 0 else 0),
    )
    if leaf_count > 0:
        graph.add_edge("root.py", "pkg/hub.py")

    for index in range(leaf_count):
        node_id = f"pkg/leaf_{index}.py"
        graph.add_node(
            node_id,
            label=f"leaf_{index}.py",
            folder="pkg",
            type="project_file",
            in_degree=1,
            out_degree=0,
            total_degree=1,
        )
        graph.add_edge("pkg/hub.py", node_id)

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
    return abs(x_coord - rect_x) <= rect_width / 2.0 and abs(y_coord - rect_y) <= rect_height / 2.0


def _node_visual_fits_inside_rect(
    node_id: str,
    render_data: bokeh_plotter.PreparedBokehRender,
    rect: tuple[float, float, float, float],
) -> bool:
    node_x, node_y = render_data.final_positions[node_id]
    rect_x, rect_y, rect_width, rect_height = rect
    node_radius = (
        render_data.node_visual_data[node_id]["viz_size"]
        / bokeh_plotter.PLOT_PIXELS_PER_LAYOUT_UNIT
        / 2.0
    )
    return (
        abs(node_x - rect_x) <= rect_width / 2.0 - node_radius
        and abs(node_y - rect_y) <= rect_height / 2.0 - node_radius
    )


def _build_render_bounds(
    render_data: bokeh_plotter.PreparedBokehRender,
) -> tuple[float, float, float, float]:
    min_x: float | None = None
    max_x: float | None = None
    min_y: float | None = None
    max_y: float | None = None

    for node_id, (x_coord, y_coord) in render_data.final_positions.items():
        node_radius = (
            render_data.node_visual_data[node_id]["viz_size"]
            / bokeh_plotter.PLOT_PIXELS_PER_LAYOUT_UNIT
            / 2.0
        )
        node_min_x = x_coord - node_radius
        node_max_x = x_coord + node_radius
        node_min_y = y_coord - node_radius
        node_max_y = y_coord + node_radius
        min_x = node_min_x if min_x is None else min(min_x, node_min_x)
        max_x = node_max_x if max_x is None else max(max_x, node_max_x)
        min_y = node_min_y if min_y is None else min(min_y, node_min_y)
        max_y = node_max_y if max_y is None else max(max_y, node_max_y)

    for rect_x, rect_y, rect_width, rect_height in _build_rect_map(
        render_data.folder_rect_data
    ).values():
        rect_min_x = rect_x - rect_width / 2.0
        rect_max_x = rect_x + rect_width / 2.0
        rect_min_y = rect_y - rect_height / 2.0
        rect_max_y = rect_y + rect_height / 2.0
        min_x = rect_min_x if min_x is None else min(min_x, rect_min_x)
        max_x = rect_max_x if max_x is None else max(max_x, rect_max_x)
        min_y = rect_min_y if min_y is None else min(min_y, rect_min_y)
        max_y = rect_max_y if max_y is None else max(max_y, rect_max_y)

    return (
        0.0 if min_x is None else min_x,
        0.0 if max_x is None else max_x,
        0.0 if min_y is None else min_y,
        0.0 if max_y is None else max_y,
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
        "viz_size": 26,
        "viz_color": bokeh_plotter.COLOR_MAP["unresolved"],
        "viz_label": "b.py",
        "viz_degree": 1,
        "viz_type": "unresolved",
        "viz_label_y_offset": 33,
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
    assert shown_plot.select_one({"type": PanTool}) is not None
    assert len(shown_plot.select({"type": Arrow})) == 1


def test_draw_bokeh_graph_uses_single_non_duplicated_toolbar_configuration(
    monkeypatch: MonkeyPatch,
) -> None:
    graph = _build_sample_graph()
    shown_plots: list[object] = []

    monkeypatch.setattr(bokeh_plotter, "_present_plot", shown_plots.append)

    bokeh_plotter.draw_bokeh_graph(graph, "constrained")

    shown_plot = cast("figure_model", shown_plots[0])
    tool_type_names = [type(tool).__name__ for tool in shown_plot.tools]
    tap_tool = cast("TapTool", shown_plot.select_one({"type": TapTool}))
    wheel_zoom_tool = cast("WheelZoomTool", shown_plot.select_one({"type": WheelZoomTool}))

    assert tool_type_names.count("PanTool") == 1
    assert tool_type_names.count("WheelZoomTool") == 1
    assert tool_type_names.count("ZoomInTool") == 1
    assert tool_type_names.count("ZoomOutTool") == 1
    assert tool_type_names.count("BoxZoomTool") == 1
    assert tool_type_names.count("ResetTool") == 1
    assert tool_type_names.count("SaveTool") == 1
    assert tool_type_names.count("TapTool") == 1
    assert tool_type_names.count("HoverTool") == 1
    assert tap_tool.visible is False
    assert cast("HoverTool", shown_plot.select_one({"type": HoverTool})).visible is False
    assert wheel_zoom_tool.visible is False
    assert wheel_zoom_tool.speed == pytest.approx(1 / 600)
    assert shown_plot.toolbar.active_scroll == "auto"
    assert type(shown_plot.toolbar.active_drag).__name__ == "PanTool"


def test_draw_bokeh_graph_places_persistent_toolbar_on_the_left(
    monkeypatch: MonkeyPatch,
) -> None:
    graph = _build_sample_graph()
    shown_plots: list[object] = []

    monkeypatch.setattr(bokeh_plotter, "_present_plot", shown_plots.append)

    bokeh_plotter.draw_bokeh_graph(graph, "constrained")

    shown_plot = cast("figure_model", shown_plots[0])
    toolbar_stylesheet = cast("InlineStyleSheet", shown_plot.toolbar.stylesheets[0])

    assert shown_plot.output_backend == "canvas"
    assert shown_plot.toolbar_location == "left"
    assert shown_plot.toolbar_inner is True
    assert shown_plot.toolbar_sticky is True
    assert shown_plot.toolbar.logo is None
    assert shown_plot.toolbar.autohide is False
    assert shown_plot.toolbar.stylesheets is not None
    assert len(shown_plot.toolbar.stylesheets) == 1
    assert "position: fixed" in toolbar_stylesheet.css
    assert "left: 16px" in toolbar_stylesheet.css


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


def test_draw_bokeh_graph_uses_browser_controller_for_generated_html(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / f"{bokeh_plotter.BOKEH_OUTPUT_PREFIX}graph.html"
    output_path.write_text("<html></html>", encoding="utf-8")
    calls: list[tuple[str, int, bool]] = []

    class RecordingController:
        def open(self, url: str, new: int, autoraise: bool) -> bool:
            calls.append((url, new, autoraise))
            return True

    def _controller_factory(browser: str | None = None) -> RecordingController:
        del browser
        return RecordingController()

    monkeypatch.setattr(bokeh_plotter, "_save_plot", lambda _plot: output_path)
    monkeypatch.setattr(
        bokeh_plotter,
        "get_browser_controller",
        _controller_factory,
    )

    message = bokeh_plotter.draw_bokeh_graph(_build_sample_graph(), "constrained")

    assert message is None
    assert calls == [(output_path.resolve().as_uri(), 2, True)]


def test_draw_bokeh_graph_uses_webbrowser_module_controller_on_macos(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / f"{bokeh_plotter.BOKEH_OUTPUT_PREFIX}graph.html"
    output_path.write_text("<html></html>", encoding="utf-8")
    calls: list[tuple[str, int, bool]] = []

    def _recording_open(url: str, new: int, autoraise: bool) -> bool:
        calls.append((url, new, autoraise))
        return True

    def _webbrowser_controller(browser: str | None = None) -> object:
        del browser
        return webbrowser

    monkeypatch.setattr(bokeh_plotter, "_save_plot", lambda _plot: output_path)
    monkeypatch.setattr(
        bokeh_plotter,
        "get_browser_controller",
        _webbrowser_controller,
    )
    monkeypatch.setattr(webbrowser, "open", _recording_open)

    message = bokeh_plotter.draw_bokeh_graph(_build_sample_graph(), "constrained")

    assert message is None
    assert calls == [(output_path.resolve().as_uri(), 2, True)]


def test_draw_bokeh_graph_returns_manual_message_for_output_path_outside_generated_html_contract(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    unexpected_output_path = tmp_path / "custom-report.txt"
    unexpected_output_path.write_text("not html", encoding="utf-8")
    controller_requested = False

    def _unexpected_controller(browser: str | None = None) -> object:
        del browser
        nonlocal controller_requested
        controller_requested = True
        return object()

    monkeypatch.setattr(
        bokeh_plotter,
        "get_browser_controller",
        _unexpected_controller,
    )

    monkeypatch.setattr(
        bokeh_plotter,
        "_save_plot",
        lambda _plot: unexpected_output_path,
    )

    message = bokeh_plotter.draw_bokeh_graph(_build_sample_graph(), "constrained")

    assert message == (
        "Interactive dependency graph saved to "
        f"{unexpected_output_path}. Automatic browser launch is unavailable in this environment; "
        "open the file manually."
    )
    assert controller_requested is False


def test_draw_bokeh_graph_returns_manual_message_for_known_unreliable_controller(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / f"{bokeh_plotter.BOKEH_OUTPUT_PREFIX}graph.html"
    output_path.write_text("<html></html>", encoding="utf-8")

    class MacOSXOSAScript:
        def __init__(self) -> None:
            self.open_calls = 0

        def open(self, url: str, new: int, autoraise: bool) -> bool:
            del url, new, autoraise
            self.open_calls += 1
            return True

    def _controller_factory(browser: str | None = None) -> MacOSXOSAScript:
        del browser
        return MacOSXOSAScript()

    monkeypatch.setattr(bokeh_plotter, "_save_plot", lambda _plot: output_path)
    monkeypatch.setattr(
        bokeh_plotter,
        "get_browser_controller",
        _controller_factory,
    )

    message = bokeh_plotter.draw_bokeh_graph(_build_sample_graph(), "constrained")

    assert message == (
        "Interactive dependency graph saved to "
        f"{output_path}. Automatic browser launch is unavailable in this environment; "
        "open the file manually."
    )


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
        assert _node_visual_fits_inside_rect(node_id, render_data, alpha_rect)

    for node_id in ("beta/c.py", "beta/d.py"):
        node_x, node_y = render_data.final_positions[node_id]
        assert _point_is_inside_rect(node_x, node_y, beta_rect)
        assert not _point_is_inside_rect(node_x, node_y, alpha_rect)
        assert _node_visual_fits_inside_rect(node_id, render_data, beta_rect)

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


def test_prepare_bokeh_render_caps_high_degree_nodes() -> None:
    render_data = bokeh_plotter.prepare_bokeh_render(_build_hub_graph(40), "constrained")
    hub_visual_data = render_data.node_visual_data["pkg/hub.py"]

    assert hub_visual_data["viz_degree"] == 41
    assert hub_visual_data["viz_size"] <= bokeh_plotter.MAX_NODE_SIZE
    assert hub_visual_data["viz_size"] > bokeh_plotter.MIN_NODE_SIZE


def test_plot_dimensions_expand_for_same_size_graph_with_larger_hub(
    monkeypatch: MonkeyPatch,
) -> None:
    shown_plots: list[object] = []

    monkeypatch.setattr(bokeh_plotter, "_present_plot", shown_plots.append)

    bokeh_plotter.draw_bokeh_graph(_build_single_folder_graph(13), "constrained")
    bokeh_plotter.draw_bokeh_graph(_build_hub_graph(12), "constrained")

    chain_plot = cast("figure_model", shown_plots[0])
    hub_plot = cast("figure_model", shown_plots[1])

    assert hub_plot.width is not None
    assert chain_plot.width is not None
    assert hub_plot.height is not None
    assert chain_plot.height is not None
    assert hub_plot.width > chain_plot.width
    assert hub_plot.height >= chain_plot.height


def test_draw_bokeh_graph_sets_initial_ranges_to_cover_full_layout(
    monkeypatch: MonkeyPatch,
) -> None:
    shown_plots: list[object] = []

    monkeypatch.setattr(bokeh_plotter, "_present_plot", shown_plots.append)

    graph = _build_hub_graph(18)
    render_data = bokeh_plotter.prepare_bokeh_render(graph, "constrained")
    min_x, max_x, min_y, max_y = _build_render_bounds(render_data)

    bokeh_plotter.draw_bokeh_graph(graph, "constrained")

    shown_plot = cast("figure_model", shown_plots[0])
    assert isinstance(shown_plot.x_range, Range1d)
    assert isinstance(shown_plot.y_range, Range1d)
    assert shown_plot.match_aspect is True
    assert isinstance(shown_plot.x_range.start, float)
    assert isinstance(shown_plot.x_range.end, float)
    assert isinstance(shown_plot.y_range.start, float)
    assert isinstance(shown_plot.y_range.end, float)
    assert shown_plot.x_range.start <= min_x
    assert shown_plot.x_range.end >= max_x
    assert shown_plot.y_range.start <= min_y
    assert shown_plot.y_range.end >= max_y


def test_draw_bokeh_graph_uses_lighter_edge_style_for_large_graphs(
    monkeypatch: MonkeyPatch,
) -> None:
    shown_plots: list[object] = []

    monkeypatch.setattr(bokeh_plotter, "_present_plot", shown_plots.append)

    bokeh_plotter.draw_bokeh_graph(_build_hub_graph(140), "constrained")

    shown_plot = cast("figure_model", shown_plots[0])
    graph_renderer = cast("GraphRenderer", shown_plot.select_one({"type": GraphRenderer}))

    assert shown_plot.output_backend == "canvas"
    assert shown_plot.lod_threshold == 1
    assert graph_renderer.edge_renderer.glyph.line_alpha == pytest.approx(0.18)
    assert graph_renderer.edge_renderer.glyph.line_width == pytest.approx(1.0)
    assert shown_plot.select_one({"type": Arrow}) is None
    assert shown_plot.select_one({"type": PanTool}) is not None
    assert type(shown_plot.toolbar.active_drag).__name__ == "PanTool"


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
