from netimport_lib.visualizer import (
    DEFAULT_VISUALIZER,
    GRAPH_LAYOUT_CHOICES,
    GRAPH_VISUALIZERS,
)


def test_visualizer_registry_has_expected_public_backends() -> None:
    assert set(GRAPH_VISUALIZERS) == {"bokeh", "mpl"}
    assert "plotly" not in GRAPH_VISUALIZERS
    assert DEFAULT_VISUALIZER == "bokeh"


def test_visualizer_defaults_are_supported_and_public_layouts_match_registry() -> None:
    public_layouts_from_registry: list[str] = []

    for visualizer in GRAPH_VISUALIZERS.values():
        assert visualizer.default_layout in visualizer.supported_layouts
        public_layouts_from_registry.extend(visualizer.supported_layouts)

    assert tuple(dict.fromkeys(public_layouts_from_registry)) == GRAPH_LAYOUT_CHOICES
