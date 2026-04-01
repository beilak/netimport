from pathlib import Path

import networkx as nx
from _pytest.monkeypatch import MonkeyPatch

from netimport_lib.graph_builder.graph_builder import (
    IgnoreConfigNode,
    build_dependency_graph,
)


def _build_graph(project_root: Path, file_imports_map: dict[str, list[str]]) -> nx.DiGraph:
    return build_dependency_graph(
        file_imports_map=file_imports_map,
        project_root=str(project_root),
        ignore=IgnoreConfigNode(nodes=set(), stdlib=False, external_lib=False),
    )


def _assert_folder_metadata(graph: nx.DiGraph, node_id: str, folder: str) -> None:
    assert graph.nodes[node_id]["folder"] == folder
    assert graph.nodes[node_id]["is_root_folder"] is False


def _assert_foreign_folders(
    graph: nx.DiGraph,
    caller_root: Path,
    node_ids: tuple[str, ...],
) -> None:
    for node_id in node_ids:
        assert graph.nodes[node_id]["folder"] != str(caller_root)


def test_build_graph_adds_unresolved_node(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    package_dir = project_root / "pkg"
    package_dir.mkdir()
    source_path = package_dir / "module.py"

    graph = _build_graph(project_root, {str(source_path): ["...helper"]})

    assert graph.has_edge(str(source_path), "...helper")
    assert graph.nodes["...helper"]["type"] == "unresolved_relative_too_many_dots"


def test_build_graph_assigns_stable_folders(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    caller_root = tmp_path / "caller"
    caller_root.mkdir()
    monkeypatch.chdir(caller_root)
    project_root = tmp_path / "workspace"
    project_root.mkdir()
    package_dir = project_root / "pkg"
    package_dir.mkdir()
    source_path = package_dir / "module.py"

    graph = _build_graph(
        project_root,
        {str(source_path): ["os", "requests", ".missing"]},
    )

    _assert_folder_metadata(graph, str(source_path), str(package_dir))
    _assert_folder_metadata(graph, "os", "Standard library")
    _assert_folder_metadata(graph, "requests", "External dependencies")
    _assert_folder_metadata(graph, ".missing", "Unresolved imports")
    _assert_foreign_folders(graph, caller_root, ("os", "requests", ".missing"))


def test_build_graph_is_deterministic(tmp_path: Path) -> None:
    project_root = tmp_path / "stable_order"
    project_root.mkdir()

    first_graph = _build_graph(
        project_root,
        {
            str(project_root / "main.py"): ["helper", "utils"],
            str(project_root / "helper.py"): [],
            str(project_root / "utils.py"): [],
        },
    )
    second_graph = _build_graph(
        project_root,
        {
            str(project_root / "utils.py"): [],
            str(project_root / "helper.py"): [],
            str(project_root / "main.py"): ["utils", "helper"],
        },
    )

    assert list(first_graph.nodes()) == list(second_graph.nodes())
    assert list(first_graph.edges()) == list(second_graph.edges())
