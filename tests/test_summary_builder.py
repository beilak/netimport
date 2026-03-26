from pathlib import Path

import networkx as nx

from netimport_lib.summary_builder import format_summary, print_summary


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
    ]


def test_print_summary_writes_formatted_lines(capsys) -> None:
    graph = _build_demo_graph()

    print_summary(graph)

    captured = capsys.readouterr()

    assert "Dependency Graph Summary" in captured.out
    assert "| Total degree           | 2.25 | 2.50   | 0   | 4   |" in captured.out
    assert "| 1    | main.py     | 0        | 4        | 4     |" in captured.out


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
