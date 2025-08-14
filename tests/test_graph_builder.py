import os
from pathlib import Path

import networkx as nx

from netimport_lib.graph_builder.graph_builder import (
    IgnoreConfigNode,
    build_dependency_graph,
)


def test_build_dependency_graph(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    (project_root / "main.py").write_text(
        """
import component
from utils import helper
"""
    )
    (project_root / "component.py").write_text(
        """
from utils import helper
"""
    )
    utils_dir = project_root / "utils"
    utils_dir.mkdir()
    (utils_dir / "helper.py").write_text("")

    file_imports_map = {
        str(project_root / "main.py"): ["component", "utils.helper"],
        str(project_root / "component.py"): ["utils.helper"],
        str(utils_dir / "helper.py"): [],
    }

    ignore_config = IgnoreConfigNode(
        nodes=set(),
        stdlib=False,
        external_lib=False,
    )

    graph = build_dependency_graph(
        file_imports_map=file_imports_map,
        project_root=str(project_root),
        ignore=ignore_config,
    )

    assert isinstance(graph, nx.DiGraph)

    expected_nodes = {
        "main.py",
        "component.py",
        "utils/helper.py",
    }
    actual_nodes = {os.path.relpath(n, project_root) for n in graph.nodes()}
    assert actual_nodes == expected_nodes

    expected_edges = {
        ("main.py", "component.py"),
        ("main.py", "utils/helper.py"),
        ("component.py", "utils/helper.py"),
    }
    actual_edges = {
        (os.path.relpath(u, project_root), os.path.relpath(v, project_root))
        for u, v in graph.edges()
    }
    assert actual_edges == expected_edges
