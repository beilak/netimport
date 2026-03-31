import webbrowser
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

from netimport_lib.visualizer import bokeh_plotter
from tests.bokeh_plotter_support.browser import (
    ControllerFactory,
    MacOSXOSAScript,
    OpenCallRecorder,
    RecordingController,
)
from tests.bokeh_plotter_support.graphs import build_sample_graph
from tests.bokeh_plotter_support.names import BokehNames


def test_manual_message_when_auto_open_skipped(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "netimport-graph.html"
    monkeypatch.setattr(bokeh_plotter, BokehNames.save_plot_attr, lambda _plot: output_path)
    monkeypatch.setattr(bokeh_plotter, BokehNames.open_saved_plot_attr, lambda _path: False)

    message = bokeh_plotter.draw_bokeh_graph(build_sample_graph(), BokehNames.constrained_layout)

    assert message == (
        "Interactive dependency graph saved to "
        f"{output_path}. Automatic browser launch is unavailable in this environment; "
        "open the file manually."
    )


def test_no_message_when_auto_open_succeeds(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "netimport-graph.html"
    monkeypatch.setattr(bokeh_plotter, BokehNames.save_plot_attr, lambda _plot: output_path)
    monkeypatch.setattr(bokeh_plotter, BokehNames.open_saved_plot_attr, lambda _path: True)

    message = bokeh_plotter.draw_bokeh_graph(build_sample_graph(), BokehNames.constrained_layout)

    assert message is None


def test_uses_browser_controller_for_html(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / f"{bokeh_plotter.BOKEH_OUTPUT_PREFIX}graph.html"
    output_path.write_text("<html></html>", encoding=BokehNames.utf8)
    calls: list[tuple[str, int, bool]] = []
    controller_factory = ControllerFactory(RecordingController(calls))

    monkeypatch.setattr(bokeh_plotter, BokehNames.save_plot_attr, lambda _plot: output_path)
    monkeypatch.setattr(
        bokeh_plotter,
        BokehNames.get_browser_controller_attr,
        controller_factory,
    )

    message = bokeh_plotter.draw_bokeh_graph(build_sample_graph(), BokehNames.constrained_layout)

    assert message is None
    assert calls == [(output_path.resolve().as_uri(), 2, True)]


def test_uses_webbrowser_controller_on_macos(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / f"{bokeh_plotter.BOKEH_OUTPUT_PREFIX}graph.html"
    output_path.write_text("<html></html>", encoding=BokehNames.utf8)
    calls: list[tuple[str, int, bool]] = []
    open_recorder = OpenCallRecorder(calls)
    controller_factory = ControllerFactory(webbrowser)

    monkeypatch.setattr(bokeh_plotter, BokehNames.save_plot_attr, lambda _plot: output_path)
    monkeypatch.setattr(
        bokeh_plotter,
        BokehNames.get_browser_controller_attr,
        controller_factory,
    )
    monkeypatch.setattr(webbrowser, "open", open_recorder)

    message = bokeh_plotter.draw_bokeh_graph(build_sample_graph(), BokehNames.constrained_layout)

    assert message is None
    assert calls == [(output_path.resolve().as_uri(), 2, True)]


def test_manual_message_for_unexpected_path(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    unexpected_output_path = tmp_path / "custom-report.txt"
    unexpected_output_path.write_text("not html", encoding=BokehNames.utf8)
    controller_factory = ControllerFactory(object())

    monkeypatch.setattr(
        bokeh_plotter,
        BokehNames.get_browser_controller_attr,
        controller_factory,
    )
    monkeypatch.setattr(
        bokeh_plotter,
        BokehNames.save_plot_attr,
        lambda _plot: unexpected_output_path,
    )

    message = bokeh_plotter.draw_bokeh_graph(build_sample_graph(), BokehNames.constrained_layout)

    assert message == (
        "Interactive dependency graph saved to "
        f"{unexpected_output_path}. Automatic browser launch is unavailable in this environment; "
        "open the file manually."
    )
    assert controller_factory.requested is False


def test_manual_message_for_unreliable_controller(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / f"{bokeh_plotter.BOKEH_OUTPUT_PREFIX}graph.html"
    output_path.write_text("<html></html>", encoding=BokehNames.utf8)
    controller_factory = ControllerFactory(MacOSXOSAScript())

    monkeypatch.setattr(bokeh_plotter, BokehNames.save_plot_attr, lambda _plot: output_path)
    monkeypatch.setattr(
        bokeh_plotter,
        BokehNames.get_browser_controller_attr,
        controller_factory,
    )

    message = bokeh_plotter.draw_bokeh_graph(build_sample_graph(), BokehNames.constrained_layout)

    assert message == (
        "Interactive dependency graph saved to "
        f"{output_path}. Automatic browser launch is unavailable in this environment; "
        "open the file manually."
    )

