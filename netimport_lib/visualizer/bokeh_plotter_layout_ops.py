"""Layout math, sizing, and packing helpers for the Bokeh visualizer."""

import math
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, cast

import networkx as nx

from netimport_lib.visualizer.bokeh_plotter_constants import CONSTANTS
from netimport_lib.visualizer.bokeh_plotter_internal_models import PackedBoxFrame
from netimport_lib.visualizer.bokeh_plotter_layout_models import (
    LayoutBounds,
    LayoutTuning,
    LocalNodeLayout,
    PackedBoxLayout,
)
from netimport_lib.visualizer.bokeh_plotter_render_models import (
    BlockScaleSpec,
    FolderLayoutBuildContext,
    LocalNodeLayoutSizing,
)
from netimport_lib.visualizer.bokeh_plotter_types import (
    CollectedFolderNodes,
    FolderHierarchy,
    LayoutPositionMap,
    NodeVisualDataMap,
)


if TYPE_CHECKING:
    from netimport_lib.visualizer.bokeh_plotter_layout_models import ContainerLayout


class _SharedOps:
    @classmethod
    def half(cls, numeric_value: float) -> float:
        return numeric_value / CONSTANTS.half_divisor

    @classmethod
    def node_item_sort_key(cls, node_item: tuple[object, object]) -> str:
        return str(node_item[0])

    @classmethod
    def named_item_sort_key(cls, named_item: tuple[str, float, float]) -> str:
        return named_item[0]

    @classmethod
    def edge_sort_key(cls, edge_item: tuple[object, object]) -> tuple[str, str]:
        return (str(edge_item[0]), str(edge_item[1]))

    @classmethod
    def folder_depth_sort_key(cls, folder_name: str) -> tuple[int, str]:
        return (folder_name.count("/"), folder_name)

    @classmethod
    def parent_folder_name(cls, folder_name: str) -> str:
        return "/".join(folder_name.split("/")[:-1])

    @classmethod
    def to_int(cls, raw_value: object) -> int:
        if isinstance(raw_value, bool):
            return int(raw_value)
        if isinstance(raw_value, int):
            return raw_value
        return 0


class _FolderDataOps:
    @classmethod
    def normalize_layout_positions(
        cls,
        raw_positions: Mapping[str, Sequence[float]],
    ) -> LayoutPositionMap:
        return {
            node_id: (float(position[0]), float(position[1]))
            for node_id, position in raw_positions.items()
        }

    @classmethod
    def collect_folder_nodes(cls, graph: nx.DiGraph) -> CollectedFolderNodes:
        folder_to_nodes: dict[str, list[str]] = {}
        root_folder_nodes: list[str] = []

        for node_id, node_data in sorted(graph.nodes(data=True), key=_SharedOps.node_item_sort_key):
            folder_name = str(node_data.get("folder", ""))
            if bool(node_data.get("is_root_folder", False)):
                root_folder_nodes.append(str(node_id))
                continue

            folder_to_nodes.setdefault(folder_name, []).append(str(node_id))

        return dict(folder_to_nodes), root_folder_nodes

    @classmethod
    def build_folder_hierarchy(
        cls,
        folder_to_nodes: Mapping[str, Sequence[str]],
    ) -> FolderHierarchy:
        all_folders = tuple(sorted(folder_to_nodes))
        root_folders: list[str] = []
        child_folders: dict[str, list[str]] = {folder_name: [] for folder_name in all_folders}

        for folder_name in all_folders:
            siblings = child_folders.get(_SharedOps.parent_folder_name(folder_name))
            if siblings is not None:
                siblings.append(folder_name)
                continue
            root_folders.append(folder_name)

        for siblings in child_folders.values():
            siblings.sort()
        root_folders.sort()

        return root_folders, child_folders

    @classmethod
    def build_sorted_layout_subgraph(
        cls,
        graph: nx.DiGraph,
        node_ids: Sequence[str],
    ) -> nx.DiGraph:
        ordered_nodes = tuple(sorted(node_ids))
        subgraph = nx.DiGraph()
        for node_id in ordered_nodes:
            subgraph.add_node(node_id)
        for start_node, end_node in sorted(
            graph.subgraph(ordered_nodes).edges(),
            key=_SharedOps.edge_sort_key,
        ):
            subgraph.add_edge(start_node, end_node)
        return subgraph


class _NodeSizeOps:
    @classmethod
    def clamp_float(cls, numeric_value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(numeric_value, maximum))

    @classmethod
    def resolve_node_size_budget(cls, node_count: int) -> tuple[int, int, float]:
        if node_count >= CONSTANTS.compact_graph_node_count_threshold:
            return (
                CONSTANTS.compact_graph_min_node_size,
                CONSTANTS.compact_graph_max_node_size,
                CONSTANTS.compact_graph_node_size_sqrt_scale,
            )
        if node_count >= CONSTANTS.medium_graph_node_count_threshold:
            return (
                CONSTANTS.medium_graph_min_node_size,
                CONSTANTS.medium_graph_max_node_size,
                CONSTANTS.medium_graph_node_size_sqrt_scale,
            )
        return (
            CONSTANTS.min_node_size,
            CONSTANTS.max_node_size,
            CONSTANTS.node_size_sqrt_scale,
        )

    @classmethod
    def calculate_node_visual_size(cls, degree: int, node_count: int) -> int:
        minimum_size, maximum_size, sqrt_scale = cls.resolve_node_size_budget(node_count)
        calculated_size = minimum_size + math.sqrt(max(degree, 0)) * sqrt_scale
        return round(cls.clamp_float(calculated_size, float(minimum_size), float(maximum_size)))

    @classmethod
    def get_node_visual_size(
        cls,
        node_visual_data: NodeVisualDataMap,
        node_id: str,
    ) -> int:
        visual_data = node_visual_data.get(node_id)
        if visual_data is None:
            return CONSTANTS.min_node_size
        return max(
            _SharedOps.to_int(visual_data.get(CONSTANTS.viz_size_field, CONSTANTS.min_node_size)), 1
        )

    @classmethod
    def node_visual_diameter_units(cls, node_visual_size: int) -> float:
        return float(node_visual_size) / CONSTANTS.plot_pixels_per_layout_unit

    @classmethod
    def node_visual_radius_units(cls, node_visual_size: int) -> float:
        return _SharedOps.half(cls.node_visual_diameter_units(node_visual_size))

    @classmethod
    def build_layout_spacing_scale(cls, node_count: int, folder_count: int) -> float:
        density_factor = math.log2(node_count + 1) / CONSTANTS.layout_density_divisor
        density_scale = 1.0 + min(1.0, density_factor)
        folder_scale = 1.0 + min(
            CONSTANTS.layout_folder_scale_limit,
            math.log2(folder_count + 1) / CONSTANTS.layout_folder_divisor,
        )
        return max(density_scale, folder_scale)


class _LocalSizingOps:
    @classmethod
    def build_layout_tuning(
        cls,
        graph: nx.DiGraph,
        folder_to_nodes: Mapping[str, Sequence[str]],
    ) -> LayoutTuning:
        node_count = max(graph.number_of_nodes(), 1)
        folder_count = max(len(folder_to_nodes), 1)
        spacing_scale = _NodeSizeOps.build_layout_spacing_scale(node_count, folder_count)
        gap_scale = 1.0 + (spacing_scale - 1.0) * CONSTANTS.layout_gap_scale_factor
        padding_scale = 1.0 + (spacing_scale - 1.0) * CONSTANTS.layout_padding_scale_factor

        return LayoutTuning(
            min_node_block_span=CONSTANTS.min_node_block_span * spacing_scale,
            node_block_cell_span=CONSTANTS.node_block_cell_span * spacing_scale,
            node_layout_inset=CONSTANTS.node_layout_inset
            * (1.0 + (spacing_scale - 1.0) * CONSTANTS.layout_inset_scale_factor),
            folder_padding_x=CONSTANTS.folder_padding_x * padding_scale,
            folder_padding_y=CONSTANTS.folder_padding_y * padding_scale,
            folder_label_height=CONSTANTS.folder_label_height * padding_scale,
            folder_section_gap=CONSTANTS.folder_section_gap * gap_scale,
            folder_grid_gap_x=CONSTANTS.folder_grid_gap_x * gap_scale,
            folder_grid_gap_y=CONSTANTS.folder_grid_gap_y * gap_scale,
            root_section_gap=CONSTANTS.root_section_gap * gap_scale,
            min_folder_content_width=CONSTANTS.min_folder_content_width * padding_scale,
            min_folder_content_height=CONSTANTS.min_folder_content_height * padding_scale,
        )

    @classmethod
    def measure_position_bounds(
        cls, raw_positions: Mapping[str, tuple[float, float]]
    ) -> LayoutBounds:
        points = tuple(raw_positions.values())
        return LayoutBounds(
            min_x=min(x_coord for x_coord, _ in points),
            max_x=max(x_coord for x_coord, _ in points),
            min_y=min(y_coord for _, y_coord in points),
            max_y=max(y_coord for _, y_coord in points),
        )

    @classmethod
    def scale_axis_value(
        cls,
        raw_value: float,
        bounds: tuple[float, float],
        usable_extent: float,
        axis_center: float,
        inset: float,
    ) -> float:
        if bounds[1] == bounds[0]:
            return axis_center
        return inset + cls.scale_axis_ratio(raw_value, bounds) * usable_extent

    @classmethod
    def scale_axis_ratio(cls, raw_value: float, bounds: tuple[float, float]) -> float:
        return (raw_value - bounds[0]) / (bounds[1] - bounds[0])

    @classmethod
    def scale_block_point(
        cls,
        raw_point: tuple[float, float],
        position_bounds: LayoutBounds,
        scale_spec: BlockScaleSpec,
    ) -> tuple[float, float]:
        usable_width = max(
            scale_spec.width - CONSTANTS.layout_position_padding_multiplier * scale_spec.inset,
            CONSTANTS.zero_float,
        )
        usable_height = max(
            scale_spec.height - CONSTANTS.layout_position_padding_multiplier * scale_spec.inset,
            CONSTANTS.zero_float,
        )
        return (
            cls.scale_axis_value(
                raw_point[0],
                (position_bounds.min_x, position_bounds.max_x),
                usable_width,
                _SharedOps.half(scale_spec.width),
                scale_spec.inset,
            ),
            cls.scale_axis_value(
                raw_point[1],
                (position_bounds.min_y, position_bounds.max_y),
                usable_height,
                _SharedOps.half(scale_spec.height),
                scale_spec.inset,
            ),
        )

    @classmethod
    def scale_positions_to_block(
        cls,
        raw_positions: Mapping[str, tuple[float, float]],
        scale_spec: BlockScaleSpec,
    ) -> LayoutPositionMap:
        if not raw_positions:
            return {}

        position_bounds = cls.measure_position_bounds(raw_positions)
        return {
            node_id: cls.scale_block_point(raw_positions[node_id], position_bounds, scale_spec)
            for node_id in sorted(raw_positions)
        }

    @classmethod
    def build_max_node_diameter_units(
        cls,
        node_ids: Sequence[str],
        node_visual_data: NodeVisualDataMap,
    ) -> float:
        return max(
            (
                _NodeSizeOps.node_visual_diameter_units(
                    _NodeSizeOps.get_node_visual_size(node_visual_data, node_id),
                )
                for node_id in node_ids
            ),
            default=CONSTANTS.zero_float,
        )


class _NodeLayoutOps:
    @classmethod
    def build_local_node_cell_span(
        cls,
        max_node_diameter_units: float,
        layout_tuning: LayoutTuning,
    ) -> float:
        return max(
            layout_tuning.node_block_cell_span,
            max_node_diameter_units * CONSTANTS.layout_position_padding_multiplier
            + CONSTANTS.node_layout_clearance_units,
        )

    @classmethod
    def build_local_node_inset(
        cls,
        max_node_diameter_units: float,
        layout_tuning: LayoutTuning,
    ) -> float:
        return max(
            layout_tuning.node_layout_inset,
            _SharedOps.half(max_node_diameter_units) + CONSTANTS.node_layout_outer_padding_units,
        )

    @classmethod
    def build_local_node_layout_sizing(
        cls,
        ordered_nodes: Sequence[str],
        context: FolderLayoutBuildContext,
    ) -> LocalNodeLayoutSizing:
        max_node_diameter_units = _LocalSizingOps.build_max_node_diameter_units(
            ordered_nodes,
            context.node_visual_data,
        )
        cell_span = cls.build_local_node_cell_span(
            max_node_diameter_units,
            context.layout_tuning,
        )
        column_count = max(1, math.ceil(math.sqrt(len(ordered_nodes))))
        return LocalNodeLayoutSizing(
            width=max(
                context.layout_tuning.min_node_block_span,
                float(column_count) * cell_span,
            ),
            height=max(
                context.layout_tuning.min_node_block_span,
                float(math.ceil(len(ordered_nodes) / column_count)) * cell_span,
            ),
            inset=cls.build_local_node_inset(max_node_diameter_units, context.layout_tuning),
            layout_k_multiplier=max(
                1.0,
                cell_span / max(context.layout_tuning.node_block_cell_span, 1.0),
            ),
        )

    @classmethod
    def build_single_node_layout(
        cls,
        node_id: str,
        layout_sizing: LocalNodeLayoutSizing,
    ) -> LocalNodeLayout:
        return LocalNodeLayout(
            width=layout_sizing.width,
            height=layout_sizing.height,
            positions={
                node_id: (
                    _SharedOps.half(layout_sizing.width),
                    _SharedOps.half(layout_sizing.height),
                )
            },
        )

    @classmethod
    def build_multi_node_layout(
        cls,
        ordered_nodes: Sequence[str],
        context: FolderLayoutBuildContext,
        layout_sizing: LocalNodeLayoutSizing,
    ) -> LocalNodeLayout:
        subgraph = _FolderDataOps.build_sorted_layout_subgraph(context.graph, ordered_nodes)
        raw_positions = _FolderDataOps.normalize_layout_positions(
            cast(
                "Mapping[str, Sequence[float]]",
                nx.spring_layout(
                    subgraph,
                    k=context.node_layout_k * layout_sizing.layout_k_multiplier,
                    iterations=CONSTANTS.spring_layout_iterations,
                    seed=CONSTANTS.freeze_random_seed,
                    scale=1,
                ),
            )
        )
        return LocalNodeLayout(
            width=layout_sizing.width,
            height=layout_sizing.height,
            positions=_LocalSizingOps.scale_positions_to_block(
                raw_positions,
                BlockScaleSpec(
                    width=layout_sizing.width,
                    height=layout_sizing.height,
                    inset=layout_sizing.inset,
                ),
            ),
        )

    @classmethod
    def build_local_node_layout(
        cls,
        node_ids: Sequence[str],
        context: FolderLayoutBuildContext,
    ) -> LocalNodeLayout:
        ordered_nodes = tuple(sorted(node_ids))
        if not ordered_nodes:
            return LocalNodeLayout(
                width=CONSTANTS.zero_float,
                height=CONSTANTS.zero_float,
                positions={},
            )

        layout_sizing = cls.build_local_node_layout_sizing(ordered_nodes, context)
        if len(ordered_nodes) == 1:
            return cls.build_single_node_layout(ordered_nodes[0], layout_sizing)
        return cls.build_multi_node_layout(ordered_nodes, context, layout_sizing)

    @classmethod
    def build_root_final_positions(cls, root_layout: object) -> LayoutPositionMap:
        container = cast("ContainerLayout", root_layout)
        return {
            node_id: (
                relative_x - _SharedOps.half(container.width),
                relative_y - _SharedOps.half(container.height),
            )
            for node_id, (relative_x, relative_y) in container.node_positions.items()
        }


class _PackingOps:
    @classmethod
    def build_single_packed_box_layout(
        cls,
        item_size: tuple[str, float, float],
    ) -> PackedBoxLayout:
        item_name, item_width, item_height = item_size
        return PackedBoxLayout(
            width=item_width,
            height=item_height,
            origins={item_name: (CONSTANTS.zero_float, CONSTANTS.zero_float)},
        )

    @classmethod
    def build_packing_grid_shape(cls, item_count: int) -> tuple[int, int]:
        column_count = max(1, math.ceil(math.sqrt(item_count)))
        return (column_count, math.ceil(item_count / column_count))

    @classmethod
    def build_packing_column_widths(
        cls,
        ordered_items: Sequence[tuple[str, float, float]],
        column_count: int,
    ) -> list[float]:
        return [
            max(
                item_width
                for item_index, (_item_name, item_width, _item_height) in enumerate(ordered_items)
                if item_index % column_count == column_index
            )
            for column_index in range(column_count)
        ]

    @classmethod
    def build_packing_row_heights(
        cls,
        ordered_items: Sequence[tuple[str, float, float]],
        column_count: int,
        row_count: int,
    ) -> list[float]:
        return [
            max(
                item_height
                for item_index, (_item_name, _item_width, item_height) in enumerate(ordered_items)
                if item_index // column_count == row_index
            )
            for row_index in range(row_count)
        ]

    @classmethod
    def build_track_total(cls, track_sizes: Sequence[float], gap_size: float) -> float:
        return sum(track_sizes) + cls.build_track_gap_total(track_sizes, gap_size)

    @classmethod
    def build_track_gap_total(cls, track_sizes: Sequence[float], gap_size: float) -> float:
        return gap_size * max(len(track_sizes) - 1, 0)

    @classmethod
    def build_track_offsets(
        cls,
        track_sizes: Sequence[float],
        gap_size: float,
    ) -> list[float]:
        offsets: list[float] = []
        current_offset: float = float(CONSTANTS.zero_float)
        for track_size in track_sizes:
            offsets.append(current_offset)
            current_offset += track_size + gap_size
        return offsets


class _PlacementOps:
    @classmethod
    def build_row_bottoms(
        cls,
        row_heights: Sequence[float],
        total_height: float,
        gap_y: float,
    ) -> list[float]:
        row_offsets = _PackingOps.build_track_offsets(row_heights, gap_y)
        return [
            total_height - row_offsets[row_index] - row_heights[row_index]
            for row_index in range(len(row_heights))
        ]

    @classmethod
    def build_packing_frame(
        cls,
        ordered_items: Sequence[tuple[str, float, float]],
        gap_x: float,
        gap_y: float,
    ) -> PackedBoxFrame:
        column_count, row_count = _PackingOps.build_packing_grid_shape(len(ordered_items))
        column_widths = _PackingOps.build_packing_column_widths(ordered_items, column_count)
        row_heights = _PackingOps.build_packing_row_heights(ordered_items, column_count, row_count)
        return PackedBoxFrame(
            column_count=column_count,
            total_width=_PackingOps.build_track_total(column_widths, gap_x),
            total_height=_PackingOps.build_track_total(row_heights, gap_y),
            column_widths=column_widths,
            row_heights=row_heights,
        )

    @classmethod
    def build_packed_box_origins(
        cls,
        ordered_items: Sequence[tuple[str, float, float]],
        packing_frame: PackedBoxFrame,
        gap_x: float,
        gap_y: float,
    ) -> dict[str, tuple[float, float]]:
        packing_offsets = cls.build_packing_offsets(packing_frame, gap_x, gap_y)
        return {
            item_name: cls.build_packed_box_origin(
                item_index,
                (item_name, item_width, item_height),
                packing_frame,
                packing_offsets,
            )
            for item_index, (item_name, item_width, item_height) in enumerate(ordered_items)
        }

    @classmethod
    def build_packing_offsets(
        cls,
        packing_frame: PackedBoxFrame,
        gap_x: float,
        gap_y: float,
    ) -> tuple[list[float], list[float]]:
        return (
            _PackingOps.build_track_offsets(packing_frame.column_widths, gap_x),
            cls.build_row_bottoms(
                packing_frame.row_heights,
                packing_frame.total_height,
                gap_y,
            ),
        )

    @classmethod
    def build_packed_box_origin(
        cls,
        item_index: int,
        item_size: tuple[str, float, float],
        packing_frame: PackedBoxFrame,
        packing_offsets: tuple[Sequence[float], Sequence[float]],
    ) -> tuple[float, float]:
        x_offsets, row_bottoms = packing_offsets
        column_index = item_index % packing_frame.column_count
        row_index = item_index // packing_frame.column_count
        return (
            x_offsets[column_index]
            + _SharedOps.half(packing_frame.column_widths[column_index] - item_size[1]),
            row_bottoms[row_index]
            + _SharedOps.half(packing_frame.row_heights[row_index] - item_size[2]),
        )

    @classmethod
    def build_multi_packed_box_layout(
        cls,
        ordered_items: Sequence[tuple[str, float, float]],
        gap_x: float,
        gap_y: float,
    ) -> PackedBoxLayout:
        packing_frame = cls.build_packing_frame(ordered_items, gap_x, gap_y)
        return PackedBoxLayout(
            width=packing_frame.total_width,
            height=packing_frame.total_height,
            origins=cls.build_packed_box_origins(ordered_items, packing_frame, gap_x, gap_y),
        )

    @classmethod
    def pack_boxes(
        cls,
        item_sizes: Sequence[tuple[str, float, float]],
        *,
        gap_x: float,
        gap_y: float,
    ) -> PackedBoxLayout:
        ordered_items = tuple(sorted(item_sizes, key=_SharedOps.named_item_sort_key))
        if not ordered_items:
            return PackedBoxLayout(
                width=CONSTANTS.zero_float,
                height=CONSTANTS.zero_float,
                origins={},
            )

        if len(ordered_items) == 1:
            return _PackingOps.build_single_packed_box_layout(ordered_items[0])
        return cls.build_multi_packed_box_layout(ordered_items, gap_x, gap_y)


# Backward-compatible public aliases preserved for existing imports and intra-package access.
SharedOps = _SharedOps
FolderDataOps = _FolderDataOps
NodeSizeOps = _NodeSizeOps
LocalSizingOps = _LocalSizingOps
NodeLayoutOps = _NodeLayoutOps
PackingOps = _PackingOps
PlacementOps = _PlacementOps
