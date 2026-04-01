"""Compatibility wrapper for Bokeh visualizer render operations."""

from netimport_lib.visualizer.bokeh_plotter.ops import render as _render_ops


_EdgeRenderOps = _render_ops._EdgeRenderOps
_GraphVisualOps = _render_ops._GraphVisualOps
_PlotDimensionsLike = _render_ops._PlotDimensionsLike
_PlotOps = _render_ops._PlotOps
_RendererSyncOps = _render_ops._RendererSyncOps
EdgeRenderOps = _render_ops.EdgeRenderOps
GraphVisualOps = _render_ops.GraphVisualOps
PlotOps = _render_ops.PlotOps
RendererSyncOps = _render_ops.RendererSyncOps
