from types import ModuleType

from netimport_lib.visualizer import bokeh_plotter_layout_ops as layout_ops
from netimport_lib.visualizer import bokeh_plotter_render_ops as render_ops
from netimport_lib.visualizer import bokeh_plotter_structure_ops as structure_ops


def _assert_public_aliases(
    module: ModuleType,
    expected_aliases: tuple[tuple[str, str], ...],
) -> None:
    for public_name, private_name in expected_aliases:
        assert getattr(module, public_name) is getattr(module, private_name)


def test_layout_ops_public_api_is_stable() -> None:
    _assert_public_aliases(
        layout_ops,
        (
            ("SharedOps", "_SharedOps"),
            ("FolderDataOps", "_FolderDataOps"),
            ("NodeSizeOps", "_NodeSizeOps"),
            ("LocalSizingOps", "_LocalSizingOps"),
            ("NodeLayoutOps", "_NodeLayoutOps"),
            ("PackingOps", "_PackingOps"),
            ("PlacementOps", "_PlacementOps"),
        ),
    )


def test_structure_ops_public_api_is_stable() -> None:
    _assert_public_aliases(
        structure_ops,
        (
            ("SectionOps", "_SectionOps"),
            ("ContainerOps", "_ContainerOps"),
            ("AssignmentOps", "_AssignmentOps"),
            ("BoundsOps", "_BoundsOps"),
            ("ConstrainedLayoutOps", "_ConstrainedLayoutOps"),
            ("PlotDimensionOps", "_PlotDimensionOps"),
            ("PlotRangeOps", "_PlotRangeOps"),
        ),
    )


def test_render_ops_public_api_is_stable() -> None:
    _assert_public_aliases(
        render_ops,
        (
            ("GraphVisualOps", "_GraphVisualOps"),
            ("PlotOps", "_PlotOps"),
            ("RendererSyncOps", "_RendererSyncOps"),
            ("EdgeRenderOps", "_EdgeRenderOps"),
        ),
    )
