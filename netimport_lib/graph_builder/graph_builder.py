import os
import networkx as nx

from netimport_lib.graph_builder.resolver_imports import resolve_import_string, normalize_path


def build_dependency_graph(
    file_imports_map: dict[str, list[str]],
    project_root: str,  # Absolute path to project root
    ignore_nodes: set[str],
) -> nx.DiGraph:
    graph = nx.DiGraph()

    normalized_project_root = normalize_path(project_root)
    # import pdb
    # pdb.set_trace()

    project_files_normalized: set[str] = set() #set(file_imports_map.keys())
    for file_path_key in file_imports_map.keys():
        project_files_normalized.add(normalize_path(file_path_key))

    # 1. Add project files as a Node
    for source_file_rel_path in project_files_normalized:
        label = os.path.basename(source_file_rel_path)
        if label in ignore_nodes:
            continue
        graph.add_node(source_file_rel_path, type="project_file", label=label)

    # 2. Imports and edges
    for source_file_rel_path, import_strings in file_imports_map.items():
        source_node_id = source_file_rel_path

        if source_node_id not in graph:
            continue

        for import_str in import_strings:
            if not import_str:
                continue

            # if import_str == "repo.account_repo.AccountRepository":
            #     import pdb
            #     pdb.set_trace()
            target_node_id, node_type = resolve_import_string(
                import_str,
                source_file_rel_path,
                # normalized_project_root,
                project_root,
                project_files_normalized,
            )
            # if target_node_id == "repo":
            #     import pdb
            #     pdb.set_trace()


            if target_node_id in ignore_nodes:
                continue

            if target_node_id is None:
                print(
                    f"Can't get ID for import '{import_str}' from '{source_file_rel_path}'."
                )
                continue

            if target_node_id not in graph:
                label = (
                    os.path.basename(target_node_id)
                    if node_type == "project_file"
                    else target_node_id
                )
                graph.add_node(target_node_id, type=node_type, label=label)

            if not graph.has_edge(source_node_id, target_node_id):
                graph.add_edge(
                    source_node_id, target_node_id, import_raw_string=import_str
                )

    return graph
