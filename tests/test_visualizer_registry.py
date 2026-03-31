import importlib
import sys

from netimport_lib.visualizer import registry as visualizer_registry


def test_visualizer_registry_public_backends() -> None:
    assert set(visualizer_registry.GRAPH_VISUALIZERS) == {"bokeh"}
    assert "plotly" not in visualizer_registry.GRAPH_VISUALIZERS
    assert visualizer_registry.DEFAULT_VISUALIZER == "bokeh"


def test_visualizer_defaults_match_public_layouts() -> None:
    public_layouts_from_registry: list[str] = []

    for visualizer in visualizer_registry.GRAPH_VISUALIZERS.values():
        assert visualizer.default_layout in visualizer.supported_layouts
        public_layouts_from_registry.extend(visualizer.supported_layouts)

    assert tuple(dict.fromkeys(public_layouts_from_registry)) == (
        visualizer_registry.GRAPH_LAYOUT_CHOICES
    )


def test_visualizer_registry_is_lazy() -> None:
    sys.modules.pop("netimport_lib.visualizer.bokeh_plotter", None)

    importlib.reload(visualizer_registry)

    assert "netimport_lib.visualizer.bokeh_plotter" not in sys.modules
