import importlib
import sys

import netimport_lib.visualizer as visualizer_module


def test_visualizer_registry_has_expected_public_backends() -> None:
    assert set(visualizer_module.GRAPH_VISUALIZERS) == {"bokeh", "mpl"}
    assert "plotly" not in visualizer_module.GRAPH_VISUALIZERS
    assert visualizer_module.DEFAULT_VISUALIZER == "bokeh"


def test_visualizer_defaults_are_supported_and_public_layouts_match_registry() -> None:
    public_layouts_from_registry: list[str] = []

    for visualizer in visualizer_module.GRAPH_VISUALIZERS.values():
        assert visualizer.default_layout in visualizer.supported_layouts
        public_layouts_from_registry.extend(visualizer.supported_layouts)

    assert tuple(dict.fromkeys(public_layouts_from_registry)) == (
        visualizer_module.GRAPH_LAYOUT_CHOICES
    )


def test_visualizer_registry_does_not_eagerly_import_render_backends() -> None:
    sys.modules.pop("netimport_lib.visualizer.bokeh_plotter_v2", None)
    sys.modules.pop("netimport_lib.visualizer.mpl_plotter", None)

    importlib.reload(visualizer_module)

    assert "netimport_lib.visualizer.bokeh_plotter_v2" not in sys.modules
    assert "netimport_lib.visualizer.mpl_plotter" not in sys.modules
