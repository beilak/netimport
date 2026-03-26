import json
from pathlib import Path

import networkx as nx
from _pytest.capture import CaptureFixture

from netimport_lib.summary_builder import (
    build_summary_payload,
    format_summary,
    format_summary_json,
    print_json_summary,
    print_summary,
)


def test_format_summary_includes_numeric_coupling_metrics() -> None:
    graph = _build_demo_graph()

    assert format_summary(graph) == [
        "Dependency Graph Summary",
        "========================",
        "+--------------------------+-------+",
        "| Metric                   | Value |",
        "+--------------------------+-------+",
        "| Nodes                    | 7     |",
        "| Edges                    | 6     |",
        "| Project files            | 4     |",
        "| Standard library modules | 1     |",
        "| External libraries       | 1     |",
        "| Unresolved imports       | 1     |",
        "+--------------------------+-------+",
        "",
        "Project Coupling Metrics",
        "========================",
        "+------------------------+------+--------+-----+-----+",
        "| Metric                 | Avg  | Median | Min | Max |",
        "+------------------------+------+--------+-----+-----+",
        "| Project files analyzed | 4    | -      | -   | -   |",
        "| Incoming degree        | 0.75 | 0.50   | 0   | 2   |",
        "| Outgoing degree        | 1.50 | 1.00   | 0   | 4   |",
        "| Total degree           | 2.25 | 2.50   | 0   | 4   |",
        "+------------------------+------+--------+-----+-----+",
        "",
        "Most Coupled Project Files",
        "==========================",
        "+------+-------------+----------+----------+-------+",
        "| Rank | File        | Incoming | Outgoing | Total |",
        "+------+-------------+----------+----------+-------+",
        "| 1    | main.py     | 0        | 4        | 4     |",
        "| 2    | helper.py   | 2        | 1        | 3     |",
        "| 3    | service.py  | 1        | 1        | 2     |",
        "| 4    | isolated.py | 0        | 0        | 0     |",
        "+------+-------------+----------+----------+-------+",
        "",
        "Least Coupled Project Files",
        "===========================",
        "+------+-------------+----------+----------+-------+",
        "| Rank | File        | Incoming | Outgoing | Total |",
        "+------+-------------+----------+----------+-------+",
        "| 1    | isolated.py | 0        | 0        | 0     |",
        "| 2    | service.py  | 1        | 1        | 2     |",
        "| 3    | helper.py   | 2        | 1        | 3     |",
        "| 4    | main.py     | 0        | 4        | 4     |",
        "+------+-------------+----------+----------+-------+",
        "",
        "Most Depended-On Project Files",
        "==============================",
        "+------+-------------+----------+----------+-------+",
        "| Rank | File        | Incoming | Outgoing | Total |",
        "+------+-------------+----------+----------+-------+",
        "| 1    | helper.py   | 2        | 1        | 3     |",
        "| 2    | service.py  | 1        | 1        | 2     |",
        "| 3    | main.py     | 0        | 4        | 4     |",
        "| 4    | isolated.py | 0        | 0        | 0     |",
        "+------+-------------+----------+----------+-------+",
        "",
        "Most Dependent Project Files",
        "============================",
        "+------+-------------+----------+----------+-------+",
        "| Rank | File        | Incoming | Outgoing | Total |",
        "+------+-------------+----------+----------+-------+",
        "| 1    | main.py     | 0        | 4        | 4     |",
        "| 2    | helper.py   | 2        | 1        | 3     |",
        "| 3    | service.py  | 1        | 1        | 2     |",
        "| 4    | isolated.py | 0        | 0        | 0     |",
        "+------+-------------+----------+----------+-------+",
        "",
        "External Dependencies",
        "=====================",
        "+------+------------+",
        "| Rank | Dependency |",
        "+------+------------+",
        "| 1    | requests   |",
        "+------+------------+",
        "",
        "Unresolved Imports",
        "==================",
        "+------+----------+---------------------+",
        "| Rank | Import   | Type                |",
        "+------+----------+---------------------+",
        "| 1    | .missing | unresolved_relative |",
        "+------+----------+---------------------+",
        "",
        "Policy Violations",
        "=================",
        "+------+---------+",
        "| Rule | Message |",
        "+------+---------+",
        "| None | -       |",
        "+------+---------+",
    ]


def test_print_summary_writes_formatted_lines(capsys: CaptureFixture[str]) -> None:
    graph = _build_demo_graph()

    print_summary(graph)

    captured = capsys.readouterr()

    assert "Dependency Graph Summary" in captured.out
    assert "| Total degree           | 2.25 | 2.50   | 0   | 4   |" in captured.out
    assert "| 1    | main.py     | 0        | 4        | 4     |" in captured.out


def test_build_summary_payload_returns_structured_data() -> None:
    graph = _build_demo_graph()

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
            {"rank": 1, "file": "main.py", "incoming": 0, "outgoing": 4, "total": 4},
            {"rank": 2, "file": "helper.py", "incoming": 2, "outgoing": 1, "total": 3},
            {"rank": 3, "file": "service.py", "incoming": 1, "outgoing": 1, "total": 2},
            {"rank": 4, "file": "isolated.py", "incoming": 0, "outgoing": 0, "total": 0},
        ],
        "least_coupled_project_files": [
            {"rank": 1, "file": "isolated.py", "incoming": 0, "outgoing": 0, "total": 0},
            {"rank": 2, "file": "service.py", "incoming": 1, "outgoing": 1, "total": 2},
            {"rank": 3, "file": "helper.py", "incoming": 2, "outgoing": 1, "total": 3},
            {"rank": 4, "file": "main.py", "incoming": 0, "outgoing": 4, "total": 4},
        ],
        "most_depended_on_project_files": [
            {"rank": 1, "file": "helper.py", "incoming": 2, "outgoing": 1, "total": 3},
            {"rank": 2, "file": "service.py", "incoming": 1, "outgoing": 1, "total": 2},
            {"rank": 3, "file": "main.py", "incoming": 0, "outgoing": 4, "total": 4},
            {"rank": 4, "file": "isolated.py", "incoming": 0, "outgoing": 0, "total": 0},
        ],
        "most_dependent_project_files": [
            {"rank": 1, "file": "main.py", "incoming": 0, "outgoing": 4, "total": 4},
            {"rank": 2, "file": "helper.py", "incoming": 2, "outgoing": 1, "total": 3},
            {"rank": 3, "file": "service.py", "incoming": 1, "outgoing": 1, "total": 2},
            {"rank": 4, "file": "isolated.py", "incoming": 0, "outgoing": 0, "total": 0},
        ],
        "external_dependencies": ["requests"],
        "unresolved_imports": [
            {"rank": 1, "import_name": ".missing", "type": "unresolved_relative"}
        ],
        "violations": [],
    }


def test_format_summary_json_returns_valid_json() -> None:
    graph = _build_demo_graph()

    formatted = format_summary_json(graph)

    assert json.loads(formatted) == build_summary_payload(graph)


def test_print_json_summary_writes_json(capsys: CaptureFixture[str]) -> None:
    graph = _build_demo_graph()

    print_json_summary(graph)

    captured = capsys.readouterr()

    assert json.loads(captured.out) == build_summary_payload(graph)


def _build_demo_graph() -> nx.DiGraph:
    project_root = Path("/virtual/netimport-summary/project")
    main_path = str(project_root / "main.py")
    service_path = str(project_root / "service.py")
    helper_path = str(project_root / "helper.py")
    isolated_path = str(project_root / "isolated.py")

    graph = nx.DiGraph()
    graph.add_node(main_path, type="project_file", label="main.py")
    graph.add_node(service_path, type="project_file", label="service.py")
    graph.add_node(helper_path, type="project_file", label="helper.py")
    graph.add_node(isolated_path, type="project_file", label="isolated.py")
    graph.add_node("os", type="std_lib", label="os")
    graph.add_node("requests", type="external_lib", label="requests")
    graph.add_node(".missing", type="unresolved_relative", label=".missing")

    graph.add_edge(main_path, service_path)
    graph.add_edge(main_path, helper_path)
    graph.add_edge(main_path, "os")
    graph.add_edge(main_path, "requests")
    graph.add_edge(service_path, helper_path)
    graph.add_edge(helper_path, ".missing")

    for node_id in graph.nodes:
        graph.nodes[node_id]["in_degree"] = graph.in_degree(node_id)
        graph.nodes[node_id]["out_degree"] = graph.out_degree(node_id)
        graph.nodes[node_id]["total_degree"] = graph.degree(node_id)

    return graph
