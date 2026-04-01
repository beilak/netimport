"""Bokeh-based graph rendering."""

import tempfile
import typing
import webbrowser
from contextlib import suppress
from pathlib import Path

import click
from bokeh import io as bokeh_io
from bokeh import models as bokeh_models

from netimport_lib.visualizer.bokeh_plotter.ops import render as render_ops
from netimport_lib.visualizer.bokeh_plotter.ops import structure as structure_ops


if typing.TYPE_CHECKING:
    import networkx as nx

    from netimport_lib.visualizer.bokeh_plotter import contracts


def get_browser_controller(browser: str | None = None) -> object:
    """Expose browser-controller lookup for runtime use and tests."""
    if browser is None:
        return webbrowser.get()
    return webbrowser.get(browser)


def _save_plot(plot: "bokeh_models.LayoutDOM") -> Path:
    constants = render_ops.__dict__["CONSTANTS"]
    with tempfile.NamedTemporaryFile(
        prefix=constants.bokeh_output_prefix,
        suffix=constants.bokeh_output_suffix,
        delete=False,
    ) as file_handle:
        output_path = Path(file_handle.name)
    bokeh_io.save(
        plot,
        filename=output_path,
        resources="cdn",
        title=constants.bokeh_plot_title,
    )
    return output_path


def _open_with_platform_default_app(output_path: Path) -> bool:
    """Fallback for local HTML when browser controllers are present but unreliable."""
    try:
        return click.launch(str(output_path), wait=False, locate=False) == 0
    except OSError:
        return False


def _open_saved_plot(output_path: Path) -> bool:
    constants = render_ops.__dict__["CONSTANTS"]
    resolved_output_path: Path | None = None
    with suppress(OSError):
        resolved_output_path = output_path.resolve(strict=True)

    if (
        resolved_output_path is None
        or not resolved_output_path.is_file()
        or not resolved_output_path.name.startswith(constants.bokeh_output_prefix)
        or resolved_output_path.suffix.lower() != constants.bokeh_output_suffix
    ):
        return False

    controller: object | None = None
    with suppress(OSError, webbrowser.Error):
        controller = get_browser_controller(None)
    # Keep this fallback chain in place. On macOS `webbrowser.get()` can return
    # `MacOSXOSAScript`, which exists but may fail to open local Bokeh HTML.
    # The CLI regression tests cover this path and should fail if it is removed.
    open_browser: object | None = None
    if controller is not None:
        open_browser = getattr(controller, "open", None)
    was_opened = False
    if (
        controller is not None
        and controller.__class__.__name__ not in constants.skipped_auto_open_controller_names
        and callable(open_browser)
    ):
        with suppress(OSError, TypeError, webbrowser.Error):
            was_opened = bool(open_browser(resolved_output_path.as_uri(), new=2, autoraise=True))
    if not was_opened:
        was_opened = _open_with_platform_default_app(resolved_output_path)
    if not was_opened and callable(open_browser):
        with suppress(OSError, TypeError, webbrowser.Error):
            was_opened = bool(open_browser(resolved_output_path.as_uri(), new=2, autoraise=True))
    return was_opened


def _present_plot(plot: "bokeh_models.LayoutDOM") -> str | None:
    output_path = _save_plot(plot)
    if _open_saved_plot(output_path):
        return None
    return (
        "Interactive dependency graph saved to "
        f"{output_path}. Automatic browser launch is unavailable in this environment; "
        "open the file manually."
    )


def prepare_bokeh_render(
    graph: "nx.DiGraph",
    layout: str,
) -> "contracts.PreparedBokehRender":
    """Prepare layout and visual attributes for Bokeh rendering."""
    node_visual_data = render_ops.GraphVisualOps.build_node_visual_data(graph)
    final_positions, folder_rect_data = structure_ops.PlotRangeOps.build_bokeh_layout(
        graph,
        layout,
        node_visual_data,
    )
    return typing.cast(
        "contracts.PreparedBokehRender",
        render_ops.__dict__["contracts"].PreparedBokehRender(
            final_positions=final_positions,
            folder_rect_data=folder_rect_data,
            arrow_source_data=render_ops.EdgeRenderOps.build_arrow_source_data(
                graph,
                final_positions,
            ),
            node_visual_data=node_visual_data,
        ),
    )


def draw_bokeh_graph(graph: "nx.DiGraph", layout: str) -> str | None:
    """Render a dependency graph with Bokeh."""
    render_data = prepare_bokeh_render(graph, layout)
    edge_style = render_ops.GraphVisualOps.build_edge_visual_style(graph)
    render_policy = render_ops.GraphVisualOps.build_render_policy(graph)
    plot = render_ops.PlotOps.build_plot_for_render(render_data, render_policy)
    render_ops.EdgeRenderOps.render_graph_on_plot(
        render_ops.GraphVisualOps.copy_graph_with_visual_data(graph, render_data.node_visual_data),
        render_data,
        edge_style,
        plot,
        show_arrows=render_policy.show_arrows,
    )
    return _present_plot(plot)
