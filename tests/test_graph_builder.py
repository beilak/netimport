import os
from pathlib import Path

import networkx as nx
from _pytest.monkeypatch import MonkeyPatch

from netimport_lib.graph_builder.graph_builder import (
    IgnoreConfigNode,
    build_dependency_graph,
)


def _relative_path(node_id: object, project_root: Path) -> str:
    return os.path.relpath(str(node_id), project_root)


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
    actual_nodes = {_relative_path(node_id, project_root) for node_id in graph.nodes()}
    assert actual_nodes == expected_nodes

    expected_edges = {
        ("main.py", "component.py"),
        ("main.py", "utils/helper.py"),
        ("component.py", "utils/helper.py"),
    }
    actual_edges = {
        (_relative_path(source_node, project_root), _relative_path(target_node, project_root))
        for source_node, target_node in graph.edges()
    }
    assert actual_edges == expected_edges


def test_build_dependency_graph_normalizes_source_file_ids(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    file_imports_map = {
        f"{project_root}/./main.py": ["helper"],
        str(project_root / "helper.py"): [],
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

    actual_edges = {
        (_relative_path(source_node, project_root), _relative_path(target_node, project_root))
        for source_node, target_node in graph.edges()
    }
    assert actual_edges == {("main.py", "helper.py")}


def test_build_dependency_graph_resolves_relative_package_imports(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    package_dir = project_root / "pkg"
    package_dir.mkdir(parents=True)

    file_imports_map = {
        str(package_dir / "__init__.py"): [],
        str(package_dir / "module.py"): ["."],
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

    actual_edges = {
        (_relative_path(source_node, project_root), _relative_path(target_node, project_root))
        for source_node, target_node in graph.edges()
    }
    assert actual_edges == {("pkg/module.py", "pkg/__init__.py")}


def test_build_dependency_graph_resolves_package_prefixed_absolute_imports(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    package_dir = project_root / "pkg"
    package_dir.mkdir(parents=True)

    file_imports_map = {
        str(project_root / "main.py"): ["project.pkg.module.ClassName"],
        str(package_dir / "module.py"): [],
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

    actual_edges = {
        (_relative_path(source_node, project_root), _relative_path(target_node, project_root))
        for source_node, target_node in graph.edges()
    }
    assert actual_edges == {("main.py", "pkg/module.py")}


def test_build_dependency_graph_adds_unresolved_relative_too_many_dots_nodes(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    package_dir = project_root / "pkg"
    package_dir.mkdir(parents=True)

    source_path = package_dir / "module.py"
    file_imports_map = {
        str(source_path): ["...helper"],
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

    assert graph.has_edge(str(source_path), "...helper")
    assert graph.nodes["...helper"]["type"] == "unresolved_relative_too_many_dots"


def test_build_dependency_graph_assigns_stable_folder_metadata_to_non_project_nodes(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    caller_root = tmp_path / "caller"
    caller_root.mkdir()
    monkeypatch.chdir(caller_root)

    project_root = tmp_path / "project"
    package_dir = project_root / "pkg"
    package_dir.mkdir(parents=True)

    source_path = package_dir / "module.py"
    file_imports_map = {
        str(source_path): ["os", "requests", ".missing"],
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

    assert graph.nodes[str(source_path)]["folder"] == str(package_dir)
    assert graph.nodes[str(source_path)]["is_root_folder"] is False
    assert graph.nodes["os"]["folder"] == "Standard library"
    assert graph.nodes["os"]["is_root_folder"] is False
    assert graph.nodes["requests"]["folder"] == "External dependencies"
    assert graph.nodes["requests"]["is_root_folder"] is False
    assert graph.nodes[".missing"]["folder"] == "Unresolved imports"
    assert graph.nodes[".missing"]["is_root_folder"] is False
    assert graph.nodes["os"]["folder"] != str(caller_root)
    assert graph.nodes["requests"]["folder"] != str(caller_root)
    assert graph.nodes[".missing"]["folder"] != str(caller_root)


def test_build_dependency_graph_is_deterministic_for_equivalent_input_orders(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    main_path = project_root / "main.py"
    helper_path = project_root / "helper.py"
    utils_path = project_root / "utils.py"

    first_input = {
        str(main_path): ["helper", "utils"],
        str(helper_path): [],
        str(utils_path): [],
    }
    second_input = {
        str(utils_path): [],
        str(helper_path): [],
        str(main_path): ["utils", "helper"],
    }
    ignore_config = IgnoreConfigNode(
        nodes=set(),
        stdlib=False,
        external_lib=False,
    )

    first_graph = build_dependency_graph(
        file_imports_map=first_input,
        project_root=str(project_root),
        ignore=ignore_config,
    )
    second_graph = build_dependency_graph(
        file_imports_map=second_input,
        project_root=str(project_root),
        ignore=ignore_config,
    )

    assert list(first_graph.nodes()) == list(second_graph.nodes())
    assert list(first_graph.edges()) == list(second_graph.edges())
