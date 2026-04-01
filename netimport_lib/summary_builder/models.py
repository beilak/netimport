"""Internal data models for dependency summary rendering."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _ProjectNodeSummary:
    node_id: str
    display_name: str
    incoming: int
    outgoing: int
    total: int


@dataclass(frozen=True, slots=True)
class _SimpleNodeSummary:
    node_id: str
    display_name: str
    node_type: str


@dataclass(frozen=True, slots=True)
class _DegreeMetricSummary:
    avg: float
    median: float
    min: int
    max: int


@dataclass(frozen=True, slots=True)
class _OverviewSummary:
    nodes: int
    edges: int
    project_files: int
    standard_library_modules: int
    external_libraries: int
    unresolved_imports: int


@dataclass(frozen=True, slots=True)
class _ProjectMetricsSummary:
    project_files_analyzed: int
    incoming_degree: _DegreeMetricSummary
    outgoing_degree: _DegreeMetricSummary
    total_degree: _DegreeMetricSummary
