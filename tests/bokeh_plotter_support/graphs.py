import networkx as nx

from tests.bokeh_plotter_support.names import BokehNames


def build_sample_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node(
        BokehNames.root_file,
        label=BokehNames.root_file,
        folder="",
        is_root_folder=True,
        type=BokehNames.project_file_type,
        in_degree=0,
        out_degree=1,
        total_degree=1,
    )
    graph.add_node(
        BokehNames.pkg_a_file,
        label="a.py",
        folder=BokehNames.pkg_folder,
        type=BokehNames.project_file_type,
        in_degree=1,
        out_degree=1,
        total_degree=2,
    )
    graph.add_node(
        BokehNames.pkg_sub_b_file,
        label=BokehNames.b_file_label,
        folder=BokehNames.pkg_sub_folder,
        type=BokehNames.unresolved_type,
        in_degree=1,
        out_degree=0,
        total_degree=1,
    )
    graph.add_edge(BokehNames.root_file, BokehNames.pkg_a_file)
    graph.add_edge(BokehNames.pkg_a_file, BokehNames.pkg_sub_b_file)
    return graph


def build_sibling_folder_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node(
        BokehNames.root_file,
        label=BokehNames.root_file,
        folder="",
        is_root_folder=True,
        type=BokehNames.project_file_type,
        in_degree=0,
        out_degree=2,
        total_degree=2,
    )
    graph.add_node(
        BokehNames.alpha_a_file,
        label="a.py",
        folder=BokehNames.alpha_folder,
        type=BokehNames.project_file_type,
        in_degree=1,
        out_degree=1,
        total_degree=2,
    )
    graph.add_node(
        BokehNames.alpha_b_file,
        label="b.py",
        folder=BokehNames.alpha_folder,
        type=BokehNames.project_file_type,
        in_degree=1,
        out_degree=1,
        total_degree=2,
    )
    graph.add_node(
        BokehNames.beta_c_file,
        label="c.py",
        folder=BokehNames.beta_folder,
        type=BokehNames.project_file_type,
        in_degree=2,
        out_degree=1,
        total_degree=3,
    )
    graph.add_node(
        BokehNames.beta_d_file,
        label="d.py",
        folder=BokehNames.beta_folder,
        type=BokehNames.project_file_type,
        in_degree=1,
        out_degree=0,
        total_degree=1,
    )
    for start_node, end_node in (
        (BokehNames.root_file, BokehNames.alpha_a_file),
        (BokehNames.root_file, BokehNames.beta_c_file),
        (BokehNames.alpha_a_file, BokehNames.alpha_b_file),
        (BokehNames.alpha_b_file, BokehNames.beta_c_file),
        (BokehNames.beta_c_file, BokehNames.beta_d_file),
    ):
        graph.add_edge(start_node, end_node)
    return graph


def build_single_folder_graph(node_count: int) -> nx.DiGraph:
    graph = nx.DiGraph()
    has_nodes = node_count > 0
    graph.add_node(
        BokehNames.root_file,
        label=BokehNames.root_file,
        folder="",
        is_root_folder=True,
        type=BokehNames.project_file_type,
        in_degree=0,
        out_degree=1 if has_nodes else 0,
        total_degree=1 if has_nodes else 0,
    )
    previous_node_id = BokehNames.root_file
    for index in range(node_count):
        node_id = f"pkg/node_{index}.py"
        graph.add_node(
            node_id,
            label=f"node_{index}.py",
            folder=BokehNames.pkg_folder,
            type=BokehNames.project_file_type,
            in_degree=1,
            out_degree=1 if index < node_count - 1 else 0,
            total_degree=2 if 0 < index < node_count - 1 else 1,
        )
        graph.add_edge(previous_node_id, node_id)
        previous_node_id = node_id
    return graph


def build_hub_graph(leaf_count: int) -> nx.DiGraph:
    graph = nx.DiGraph()
    has_leaves = leaf_count > 0
    graph.add_node(
        BokehNames.root_file,
        label=BokehNames.root_file,
        folder="",
        is_root_folder=True,
        type=BokehNames.project_file_type,
        in_degree=0,
        out_degree=int(has_leaves),
        total_degree=int(has_leaves),
    )
    graph.add_node(
        BokehNames.pkg_hub_file,
        label="hub.py",
        folder=BokehNames.pkg_folder,
        type=BokehNames.project_file_type,
        in_degree=int(has_leaves),
        out_degree=leaf_count,
        total_degree=leaf_count + int(has_leaves),
    )
    if has_leaves:
        graph.add_edge(BokehNames.root_file, BokehNames.pkg_hub_file)
    for index in range(leaf_count):
        node_id = f"pkg/leaf_{index}.py"
        graph.add_node(
            node_id,
            label=f"leaf_{index}.py",
            folder=BokehNames.pkg_folder,
            type=BokehNames.project_file_type,
            in_degree=1,
            out_degree=0,
            total_degree=1,
        )
        graph.add_edge(BokehNames.pkg_hub_file, node_id)
    return graph

