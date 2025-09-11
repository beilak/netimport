import textwrap

import networkx as nx
import numpy as np


def print_summary(graph: nx.DiGraph) -> None:
    if not graph.nodes:
        print("The project is empty.")
        return

    print_header("Dependency Graph Summary")
    print_top_10_files(graph)
    print_link_statistics(graph)
    print_external_dependencies(graph)


def print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(f"| {title:^76} |")
    print("=" * 80 + "\n")


def print_top_10_files(graph: nx.DiGraph) -> None:
    print_header("Top-10 Files by Number of Links")
    nodes = graph.nodes(data=True)
    sorted_nodes = sorted(nodes, key=lambda item: item[1].get('total_degree', 0), reverse=True)
    for i, (node_id, data) in enumerate(sorted_nodes[:10]):
        total = data.get('total_degree', 0)
        incoming = data.get('in_degree', 0)
        print(f"{i + 1}. {node_id} - {total} links ({incoming} incoming)")


def print_link_statistics(graph: nx.DiGraph) -> None:
    print_header("Link Statistics (Total Links per File)")
    degrees = [data.get('total_degree', 0) for _, data in graph.nodes(data=True)]
    if not degrees:
        print("No links found in the project.")
        return

    print(f" - Median: {np.median(degrees):.2f}")
    print(f" - Standard Deviation: {np.std(degrees):.2f}")
    print(f" - Mean: {np.mean(degrees):.2f}")
    print(f" - Min: {np.min(degrees)}")
    print(f" - Max: {np.max(degrees)}")


def print_external_dependencies(graph: nx.DiGraph) -> None:
    print_header("External Library Dependencies")
    external_deps = [
        node
        for node, data in graph.nodes(data=True)
        if data.get("type") == "external_lib"
    ]
    if not external_deps:
        print("No external library dependencies found.")
        return

    print("External libraries used in this project:")
    for dep in sorted(external_deps):
        print(f" - {dep}")
