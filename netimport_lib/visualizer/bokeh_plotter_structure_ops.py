"""Compatibility wrapper for Bokeh visualizer structure operations."""

from netimport_lib.visualizer.bokeh_plotter.ops import structure as _structure_ops


_AssignmentOps = _structure_ops._AssignmentOps
_BoundsOps = _structure_ops._BoundsOps
_ConstrainedLayoutOps = _structure_ops._ConstrainedLayoutOps
_ContainerOps = _structure_ops._ContainerOps
_PlotDimensionOps = _structure_ops._PlotDimensionOps
_PlotRangeOps = _structure_ops._PlotRangeOps
_SectionOps = _structure_ops._SectionOps
AssignmentOps = _structure_ops.AssignmentOps
BoundsOps = _structure_ops.BoundsOps
ConstrainedLayoutOps = _structure_ops.ConstrainedLayoutOps
ContainerOps = _structure_ops.ContainerOps
PlotDimensionOps = _structure_ops.PlotDimensionOps
PlotRangeOps = _structure_ops.PlotRangeOps
SectionOps = _structure_ops.SectionOps
