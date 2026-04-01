import json

from _pytest.capture import CaptureFixture

from netimport_lib.summary_builder import (
    build_summary_payload,
    format_summary_json,
    print_json_summary,
)
from tests.summary_builder_support import (
    SummaryNames,
    build_demo_graph,
    project_summary_row,
    unresolved_import_row,
)


def test_build_summary_payload() -> None:
    graph = build_demo_graph()

    assert build_summary_payload(graph) == {
        "schema_version": 1,
        "overview": {
            "nodes": 7,
            "edges": 6,
            "project_files": 4,
            "standard_library_modules": 1,
            "external_libraries": 1,
            "unresolved_imports": 1,
        },
        "project_metrics": {
            "project_files_analyzed": 4,
            "incoming_degree": {"avg": 0.75, "median": 0.5, "min": 0, "max": 2},
            "outgoing_degree": {"avg": 1.5, "median": 1.0, "min": 0, "max": 4},
            "total_degree": {"avg": 2.25, "median": 2.5, "min": 0, "max": 4},
        },
        "most_coupled_project_files": [
            project_summary_row(1, SummaryNames.main_file, incoming=0, outgoing=4, total=4),
            project_summary_row(2, SummaryNames.helper_file, incoming=2, outgoing=1, total=3),
            project_summary_row(3, SummaryNames.service_file, incoming=1, outgoing=1, total=2),
            project_summary_row(4, SummaryNames.isolated_file, incoming=0, outgoing=0, total=0),
        ],
        "least_coupled_project_files": [
            project_summary_row(1, SummaryNames.isolated_file, incoming=0, outgoing=0, total=0),
            project_summary_row(2, SummaryNames.service_file, incoming=1, outgoing=1, total=2),
            project_summary_row(3, SummaryNames.helper_file, incoming=2, outgoing=1, total=3),
            project_summary_row(4, SummaryNames.main_file, incoming=0, outgoing=4, total=4),
        ],
        "most_depended_on_project_files": [
            project_summary_row(1, SummaryNames.helper_file, incoming=2, outgoing=1, total=3),
            project_summary_row(2, SummaryNames.service_file, incoming=1, outgoing=1, total=2),
            project_summary_row(3, SummaryNames.main_file, incoming=0, outgoing=4, total=4),
            project_summary_row(4, SummaryNames.isolated_file, incoming=0, outgoing=0, total=0),
        ],
        "most_dependent_project_files": [
            project_summary_row(1, SummaryNames.main_file, incoming=0, outgoing=4, total=4),
            project_summary_row(2, SummaryNames.helper_file, incoming=2, outgoing=1, total=3),
            project_summary_row(3, SummaryNames.service_file, incoming=1, outgoing=1, total=2),
            project_summary_row(4, SummaryNames.isolated_file, incoming=0, outgoing=0, total=0),
        ],
        "external_dependencies": [SummaryNames.requests_lib],
        "unresolved_imports": [unresolved_import_row(1, SummaryNames.missing_import)],
        "violations": [],
    }


def test_format_summary_json_returns_valid_json() -> None:
    graph = build_demo_graph()

    formatted = format_summary_json(graph)

    assert json.loads(formatted) == build_summary_payload(graph)


def test_print_json_summary_writes_json(capsys: CaptureFixture[str]) -> None:
    graph = build_demo_graph()
    print_json_summary(graph)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == build_summary_payload(graph)
