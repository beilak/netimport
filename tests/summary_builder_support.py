from pathlib import Path

import networkx as nx


class SummaryNames:
    rank_table_border = "+------+-------------+----------+----------+-------+"
    rank_table_header = "| Rank | File        | Incoming | Outgoing | Total |"
    rank_key = "rank"
    file_key = "file"
    incoming_key = "incoming"
    outgoing_key = "outgoing"
    total_key = "total"
    main_file = "main.py"
    helper_file = "helper.py"
    service_file = "service.py"
    isolated_file = "isolated.py"
    project_file_type = "project_file"
    requests_lib = "requests"
    missing_import = ".missing"


def project_summary_row(
    rank: int,
    file_name: str,
    *,
    incoming: int,
    outgoing: int,
    total: int,
) -> dict[str, int | str]:
    return {
        SummaryNames.rank_key: rank,
        SummaryNames.file_key: file_name,
        SummaryNames.incoming_key: incoming,
        SummaryNames.outgoing_key: outgoing,
        SummaryNames.total_key: total,
    }


def unresolved_import_row(rank: int, import_name: str) -> dict[str, int | str]:
    return {
        SummaryNames.rank_key: rank,
        "import_name": import_name,
        "type": "unresolved_relative",
    }


def _build_project_paths(project_root: Path) -> dict[str, str]:
    return {
        SummaryNames.main_file: str(project_root / SummaryNames.main_file),
        SummaryNames.service_file: str(project_root / SummaryNames.service_file),
        SummaryNames.helper_file: str(project_root / SummaryNames.helper_file),
        SummaryNames.isolated_file: str(project_root / SummaryNames.isolated_file),
    }


def _connect_demo_graph(graph: nx.DiGraph, project_paths: dict[str, str]) -> None:
    graph.add_edge(
        project_paths[SummaryNames.main_file],
        project_paths[SummaryNames.service_file],
    )
    graph.add_edge(
        project_paths[SummaryNames.main_file],
        project_paths[SummaryNames.helper_file],
    )
    graph.add_edge(project_paths[SummaryNames.main_file], "os")
    graph.add_edge(project_paths[SummaryNames.main_file], SummaryNames.requests_lib)
    graph.add_edge(
        project_paths[SummaryNames.service_file],
        project_paths[SummaryNames.helper_file],
    )
    graph.add_edge(project_paths[SummaryNames.helper_file], SummaryNames.missing_import)


def build_demo_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    project_root = Path("/virtual/netimport-summary/project")
    project_paths = _build_project_paths(project_root)
    for label, node_id in project_paths.items():
        graph.add_node(node_id, type=SummaryNames.project_file_type, label=label)
    graph.add_node("os", type="std_lib", label="os")
    graph.add_node(
        SummaryNames.requests_lib,
        type="external_lib",
        label=SummaryNames.requests_lib,
    )
    graph.add_node(
        SummaryNames.missing_import,
        type="unresolved_relative",
        label=SummaryNames.missing_import,
    )
    _connect_demo_graph(graph, project_paths)
    for node_id in tuple(str(raw_node_id) for raw_node_id in graph.nodes):
        graph.nodes[node_id]["in_degree"] = graph.in_degree(node_id)
        graph.nodes[node_id]["out_degree"] = graph.out_degree(node_id)
        graph.nodes[node_id]["total_degree"] = graph.degree(node_id)
    return graph
