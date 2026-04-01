from pathlib import Path

import networkx as nx

from netimport_lib.graph_builder.graph_builder import (
    IgnoreConfigNode,
    build_dependency_graph,
)


def _relative_path(node_id: object, project_root: Path) -> str:
    return str(Path(str(node_id)).relative_to(project_root))


def _relative_graph(
    graph: nx.DiGraph,
    project_root: Path,
) -> tuple[set[str], set[object]]:
    return (
        {_relative_path(node_id, project_root) for node_id in graph.nodes()},
        {
            (
                _relative_path(source_node, project_root),
                _relative_path(target_node, project_root),
            )
            for source_node, target_node in graph.edges()
        },
    )


def _build_dependency_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    main_path = project_root / "main.py"
    component_path = project_root / "component.py"
    helper_path = project_root / "deps" / "helper.py"
    helper_path.parent.mkdir()
    main_path.write_text("import component\nfrom deps import helper\n")
    component_path.write_text("from deps import helper\n")
    helper_path.write_text("")
    return project_root, main_path, component_path, helper_path


def test_build_dependency_graph(tmp_path: Path) -> None:
    project_root, main_path, component_path, helper_path = _build_dependency_fixture(tmp_path)

    graph = build_dependency_graph(
        file_imports_map={
            str(main_path): ["component", "deps.helper"],
            str(component_path): ["deps.helper"],
            str(helper_path): [],
        },
        project_root=str(project_root),
        ignore=IgnoreConfigNode(nodes=set(), stdlib=False, external_lib=False),
    )

    assert isinstance(graph, nx.DiGraph)
    assert _relative_graph(graph, project_root)[0] == {
        main_path.name,
        component_path.name,
        str(helper_path.relative_to(project_root)),
    }
    assert _relative_graph(graph, project_root)[1] == {
        (main_path.name, component_path.name),
        (main_path.name, str(helper_path.relative_to(project_root))),
        (component_path.name, str(helper_path.relative_to(project_root))),
    }


def test_build_graph_normalizes_source_ids(tmp_path: Path) -> None:
    project_root = tmp_path / "workspace"
    project_root.mkdir()

    graph = build_dependency_graph(
        file_imports_map={
            f"{project_root}/./app.py": ["helper"],
            str(project_root / "helper.py"): [],
        },
        project_root=str(project_root),
        ignore=IgnoreConfigNode(nodes=set(), stdlib=False, external_lib=False),
    )

    assert _relative_graph(graph, project_root)[1] == {("app.py", "helper.py")}


def test_build_graph_rel_pkg_imports(tmp_path: Path) -> None:
    project_root = tmp_path / "analysis"
    project_root.mkdir()
    package_dir = project_root / "pkg"
    package_dir.mkdir()

    graph = build_dependency_graph(
        file_imports_map={
            str(package_dir / "__init__.py"): [],
            str(package_dir / "node.py"): ["."],
        },
        project_root=str(project_root),
        ignore=IgnoreConfigNode(nodes=set(), stdlib=False, external_lib=False),
    )

    assert _relative_graph(graph, project_root)[1] == {("pkg/node.py", "pkg/__init__.py")}


def test_build_graph_pkg_prefixed_imports(tmp_path: Path) -> None:
    project_root = tmp_path / "package_root"
    project_root.mkdir()
    package_dir = project_root / "package"
    package_dir.mkdir()

    graph = build_dependency_graph(
        file_imports_map={
            str(project_root / "entry.py"): ["package_root.package.member.ClassName"],
            str(package_dir / "member.py"): [],
        },
        project_root=str(project_root),
        ignore=IgnoreConfigNode(nodes=set(), stdlib=False, external_lib=False),
    )

    assert _relative_graph(graph, project_root)[1] == {("entry.py", "package/member.py")}
