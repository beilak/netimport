"""Container, bounds, and plot-range helpers for the Bokeh visualizer."""

from __future__ import annotations
import math
import typing

from bokeh import models as bokeh_models

from netimport_lib.visualizer import bokeh_plotter_contracts as contracts
from netimport_lib.visualizer import bokeh_plotter_internal_models as internal_models
from netimport_lib.visualizer import bokeh_plotter_layout_models as layout_models
from netimport_lib.visualizer import bokeh_plotter_layout_ops as layout_ops
from netimport_lib.visualizer import bokeh_plotter_render_models as render_models
from netimport_lib.visualizer import bokeh_plotter_types as plot_types
from netimport_lib.visualizer.bokeh_plotter_constants import CONSTANTS


if typing.TYPE_CHECKING:
    import networkx as nx


class _SectionOps:
    @classmethod
    def should_use_side_by_side_sections(
        cls,
        packed_children: layout_models.PackedBoxLayout,
        direct_nodes_layout: layout_models.LocalNodeLayout,
        layout_tuning: layout_models.LayoutTuning,
    ) -> bool:
        if not packed_children.width or not direct_nodes_layout.width:
            return False

        combined_area = (
            packed_children.width * packed_children.height
            + direct_nodes_layout.width * direct_nodes_layout.height
        )
        return (
            combined_area
            >= (layout_tuning.node_block_cell_span**2) * CONSTANTS.side_by_side_area_threshold
        )

    @classmethod
    def build_child_box_sizes(
        cls,
        child_names: typing.Sequence[str],
        folder_layouts: typing.Mapping[str, layout_models.ContainerLayout],
    ) -> list[tuple[str, float, float]]:
        return [
            (child_name, folder_layouts[child_name].width, folder_layouts[child_name].height)
            for child_name in child_names
        ]

    @classmethod
    def build_root_child_sizes(
        cls,
        root_folders: typing.Sequence[str],
        folder_layouts: typing.Mapping[str, layout_models.ContainerLayout],
    ) -> list[tuple[str, float, float]]:
        return [
            (folder_name, folder_layouts[folder_name].width, folder_layouts[folder_name].height)
            for folder_name in sorted(root_folders)
        ]

    @classmethod
    def build_section_gap(
        cls,
        primary_height: float,
        secondary_height: float,
        section_gap: float,
    ) -> float:
        if primary_height and secondary_height:
            return section_gap
        return float(CONSTANTS.zero_float)

    @classmethod
    def build_side_by_side_folder_placement(
        cls,
        packed_children: layout_models.PackedBoxLayout,
        direct_nodes_layout: layout_models.LocalNodeLayout,
        layout_tuning: layout_models.LayoutTuning,
    ) -> internal_models.SectionPlacement:
        section_gap = cls.build_section_gap(
            packed_children.height,
            direct_nodes_layout.height,
            layout_tuning.folder_section_gap,
        )
        content_width = max(
            layout_tuning.min_folder_content_width,
            packed_children.width + direct_nodes_layout.width + section_gap,
        )
        content_height = max(
            layout_tuning.min_folder_content_height,
            packed_children.height,
            direct_nodes_layout.height,
        )
        child_origin_x = layout_tuning.folder_padding_x + layout_ops.SharedOps.half(
            content_width - packed_children.width - direct_nodes_layout.width - section_gap,
        )
        return internal_models.SectionPlacement(
            total_width=content_width,
            total_height=content_height,
            primary_origin=(
                child_origin_x,
                layout_tuning.folder_padding_y
                + layout_ops.SharedOps.half(content_height - packed_children.height),
            ),
            secondary_origin=(
                child_origin_x + packed_children.width + section_gap,
                layout_tuning.folder_padding_y
                + layout_ops.SharedOps.half(content_height - direct_nodes_layout.height),
            ),
        )

    @classmethod
    def build_stacked_folder_placement(
        cls,
        packed_children: layout_models.PackedBoxLayout,
        direct_nodes_layout: layout_models.LocalNodeLayout,
        layout_tuning: layout_models.LayoutTuning,
    ) -> internal_models.SectionPlacement:
        section_gap = cls.build_section_gap(
            packed_children.height,
            direct_nodes_layout.height,
            layout_tuning.folder_section_gap,
        )
        content_width = max(
            layout_tuning.min_folder_content_width,
            direct_nodes_layout.width,
            packed_children.width,
        )
        content_height = max(
            layout_tuning.min_folder_content_height,
            packed_children.height + direct_nodes_layout.height + section_gap,
        )
        return internal_models.SectionPlacement(
            total_width=content_width,
            total_height=content_height,
            primary_origin=(
                layout_tuning.folder_padding_x
                + layout_ops.SharedOps.half(content_width - packed_children.width),
                layout_tuning.folder_padding_y,
            ),
            secondary_origin=(
                layout_tuning.folder_padding_x
                + layout_ops.SharedOps.half(content_width - direct_nodes_layout.width),
                layout_tuning.folder_padding_y + packed_children.height + section_gap,
            ),
        )

    @classmethod
    def build_folder_section_placement(
        cls,
        packed_children: layout_models.PackedBoxLayout,
        direct_nodes_layout: layout_models.LocalNodeLayout,
        layout_tuning: layout_models.LayoutTuning,
    ) -> internal_models.SectionPlacement:
        if cls.should_use_side_by_side_sections(
            packed_children,
            direct_nodes_layout,
            layout_tuning,
        ):
            return cls.build_side_by_side_folder_placement(
                packed_children,
                direct_nodes_layout,
                layout_tuning,
            )
        return cls.build_stacked_folder_placement(
            packed_children,
            direct_nodes_layout,
            layout_tuning,
        )


class _ContainerOps:
    @classmethod
    def offset_layout_positions(
        cls,
        relative_positions: plot_types.LayoutPositionMap,
        origin_x: float,
        origin_y: float,
    ) -> plot_types.LayoutPositionMap:
        return {
            item_name: (origin_x + local_x, origin_y + local_y)
            for item_name, (local_x, local_y) in relative_positions.items()
        }

    @classmethod
    def finalize_folder_container_layout(
        cls,
        direct_nodes_layout: layout_models.LocalNodeLayout,
        packed_children: layout_models.PackedBoxLayout,
        layout_tuning: layout_models.LayoutTuning,
    ) -> layout_models.ContainerLayout:
        section_placement = _SectionOps.build_folder_section_placement(
            packed_children,
            direct_nodes_layout,
            layout_tuning,
        )
        primary_origin = section_placement.primary_origin
        secondary_origin = section_placement.secondary_origin
        return layout_models.ContainerLayout(
            width=(
                section_placement.total_width
                + CONSTANTS.layout_position_padding_multiplier * layout_tuning.folder_padding_x
            ),
            height=(
                section_placement.total_height
                + CONSTANTS.layout_position_padding_multiplier * layout_tuning.folder_padding_y
                + layout_tuning.folder_label_height
            ),
            node_positions=cls.offset_layout_positions(
                direct_nodes_layout.positions,
                secondary_origin[0],
                secondary_origin[1],
            ),
            child_origins=cls.offset_layout_positions(
                packed_children.origins,
                primary_origin[0],
                primary_origin[1],
            ),
        )

    @classmethod
    def build_folder_container_layout(
        cls,
        folder_name: str,
        folder_layouts: typing.Mapping[str, layout_models.ContainerLayout],
        context: render_models.FolderLayoutBuildContext,
    ) -> layout_models.ContainerLayout:
        direct_nodes_layout = layout_ops.NodeLayoutOps.build_local_node_layout(
            context.folder_to_nodes.get(folder_name, ()),
            context,
        )
        child_box_sizes = _SectionOps.build_child_box_sizes(
            tuple(sorted(context.child_folders.get(folder_name, ()))),
            folder_layouts,
        )
        packed_children = layout_ops.PlacementOps.pack_boxes(
            child_box_sizes,
            gap_x=context.layout_tuning.folder_grid_gap_x,
            gap_y=context.layout_tuning.folder_grid_gap_y,
        )
        return cls.finalize_folder_container_layout(
            direct_nodes_layout,
            packed_children,
            context.layout_tuning,
        )

    @classmethod
    def build_side_by_side_root_placement(
        cls,
        packed_root_folders: layout_models.PackedBoxLayout,
        root_nodes_layout: layout_models.LocalNodeLayout,
        root_section_gap: float,
    ) -> internal_models.SectionPlacement:
        total_height = max(packed_root_folders.height, root_nodes_layout.height)
        return internal_models.SectionPlacement(
            total_width=packed_root_folders.width + root_nodes_layout.width + root_section_gap,
            total_height=total_height,
            primary_origin=(
                float(CONSTANTS.zero_float),
                layout_ops.SharedOps.half(total_height - packed_root_folders.height),
            ),
            secondary_origin=(
                packed_root_folders.width + root_section_gap,
                layout_ops.SharedOps.half(total_height - root_nodes_layout.height),
            ),
        )

    @classmethod
    def build_stacked_root_placement(
        cls,
        packed_root_folders: layout_models.PackedBoxLayout,
        root_nodes_layout: layout_models.LocalNodeLayout,
        root_section_gap: float,
    ) -> internal_models.SectionPlacement:
        total_width = max(root_nodes_layout.width, packed_root_folders.width)
        return internal_models.SectionPlacement(
            total_width=total_width,
            total_height=packed_root_folders.height + root_nodes_layout.height + root_section_gap,
            primary_origin=(
                layout_ops.SharedOps.half(total_width - packed_root_folders.width),
                float(CONSTANTS.zero_float),
            ),
            secondary_origin=(
                layout_ops.SharedOps.half(total_width - root_nodes_layout.width),
                packed_root_folders.height + root_section_gap,
            ),
        )

    @classmethod
    def build_root_section_placement(
        cls,
        packed_root_folders: layout_models.PackedBoxLayout,
        root_nodes_layout: layout_models.LocalNodeLayout,
        layout_tuning: layout_models.LayoutTuning,
    ) -> internal_models.SectionPlacement:
        root_section_gap = _SectionOps.build_section_gap(
            packed_root_folders.height,
            root_nodes_layout.height,
            layout_tuning.root_section_gap,
        )
        if _SectionOps.should_use_side_by_side_sections(
            packed_root_folders,
            root_nodes_layout,
            layout_tuning,
        ):
            return cls.build_side_by_side_root_placement(
                packed_root_folders,
                root_nodes_layout,
                root_section_gap,
            )
        return cls.build_stacked_root_placement(
            packed_root_folders,
            root_nodes_layout,
            root_section_gap,
        )

    @classmethod
    def finalize_root_container_layout(
        cls,
        root_nodes_layout: layout_models.LocalNodeLayout,
        packed_root_folders: layout_models.PackedBoxLayout,
        layout_tuning: layout_models.LayoutTuning,
    ) -> layout_models.ContainerLayout:
        section_placement = cls.build_root_section_placement(
            packed_root_folders,
            root_nodes_layout,
            layout_tuning,
        )
        primary_origin = section_placement.primary_origin
        secondary_origin = section_placement.secondary_origin
        return layout_models.ContainerLayout(
            width=section_placement.total_width,
            height=section_placement.total_height,
            node_positions=cls.offset_layout_positions(
                root_nodes_layout.positions,
                secondary_origin[0],
                secondary_origin[1],
            ),
            child_origins=cls.offset_layout_positions(
                packed_root_folders.origins,
                primary_origin[0],
                primary_origin[1],
            ),
        )


class _AssignmentOps:
    @classmethod
    def build_root_container_layout(
        cls,
        root_folder_nodes: typing.Sequence[str],
        root_folders: typing.Sequence[str],
        folder_layouts: typing.Mapping[str, layout_models.ContainerLayout],
        context: render_models.FolderLayoutBuildContext,
    ) -> layout_models.ContainerLayout:
        root_nodes_layout = layout_ops.NodeLayoutOps.build_local_node_layout(
            root_folder_nodes, context
        )
        root_child_sizes = _SectionOps.build_root_child_sizes(root_folders, folder_layouts)
        packed_root_folders = layout_ops.PlacementOps.pack_boxes(
            root_child_sizes,
            gap_x=context.layout_tuning.folder_grid_gap_x,
            gap_y=context.layout_tuning.folder_grid_gap_y,
        )
        return _ContainerOps.finalize_root_container_layout(
            root_nodes_layout,
            packed_root_folders,
            context.layout_tuning,
        )

    @classmethod
    def build_folder_rect_data(cls) -> contracts.FolderRectData:
        return contracts.FolderRectData()

    @classmethod
    def assign_layout_node_positions(
        cls,
        origin_x: float,
        origin_y: float,
        layout: layout_models.ContainerLayout,
        final_positions: plot_types.LayoutPositionMap,
    ) -> None:
        for node_id in sorted(layout.node_positions):
            relative_x, relative_y = layout.node_positions[node_id]
            final_positions[node_id] = (origin_x + relative_x, origin_y + relative_y)

    @classmethod
    def assign_child_layout_positions(
        cls,
        origin_x: float,
        origin_y: float,
        layout: layout_models.ContainerLayout,
        assignment: render_models.FolderPositionAssignment,
    ) -> None:
        for child_name in sorted(layout.child_origins):
            child_origin_x, child_origin_y = layout.child_origins[child_name]
            cls.assign_folder_positions(
                child_name,
                origin_x + child_origin_x,
                origin_y + child_origin_y,
                assignment,
            )

    @classmethod
    def assign_folder_positions(
        cls,
        folder_name: str,
        origin_x: float,
        origin_y: float,
        assignment: render_models.FolderPositionAssignment,
    ) -> None:
        layout = assignment.folder_layouts[folder_name]
        assignment.folder_rect_data.append_folder(
            folder_name,
            origin_x,
            origin_y,
            layout,
            assignment.layout_tuning,
        )
        cls.assign_layout_node_positions(origin_x, origin_y, layout, assignment.final_positions)
        cls.assign_child_layout_positions(origin_x, origin_y, layout, assignment)

    @classmethod
    def append_layout_bounds(
        cls,
        horizontal_bounds: list[tuple[float, float]],
        vertical_bounds: list[tuple[float, float]],
        horizontal_range: tuple[float, float],
        vertical_range: tuple[float, float],
    ) -> None:
        horizontal_bounds.append(horizontal_range)
        vertical_bounds.append(vertical_range)

    @classmethod
    def build_node_layout_bounds(
        cls,
        final_positions: plot_types.LayoutPositionMap,
        node_visual_data: plot_types.NodeVisualDataMap,
        horizontal_bounds: list[tuple[float, float]],
        vertical_bounds: list[tuple[float, float]],
    ) -> None:
        for node_id, (x_coord, y_coord) in final_positions.items():
            node_radius = layout_ops.NodeSizeOps.node_visual_radius_units(
                layout_ops.NodeSizeOps.get_node_visual_size(node_visual_data, node_id),
            )
            cls.append_layout_bounds(
                horizontal_bounds,
                vertical_bounds,
                (x_coord - node_radius, x_coord + node_radius),
                (y_coord - node_radius, y_coord + node_radius),
            )


class _BoundsOps:
    @classmethod
    def build_folder_layout_bounds(
        cls,
        folder_rect_data: contracts.FolderRectData,
        horizontal_bounds: list[tuple[float, float]],
        vertical_bounds: list[tuple[float, float]],
    ) -> None:
        for center_x, center_y, width, height in zip(
            folder_rect_data.center_xs,
            folder_rect_data.center_ys,
            folder_rect_data.widths,
            folder_rect_data.heights,
            strict=True,
        ):
            _AssignmentOps.append_layout_bounds(
                horizontal_bounds,
                vertical_bounds,
                (
                    center_x - layout_ops.SharedOps.half(width),
                    center_x + layout_ops.SharedOps.half(width),
                ),
                (
                    center_y - layout_ops.SharedOps.half(height),
                    center_y + layout_ops.SharedOps.half(height),
                ),
            )

    @classmethod
    def empty_layout_bounds(cls) -> layout_models.LayoutBounds:
        return layout_models.LayoutBounds(
            min_x=CONSTANTS.zero_float,
            max_x=CONSTANTS.zero_float,
            min_y=CONSTANTS.zero_float,
            max_y=CONSTANTS.zero_float,
        )

    @classmethod
    def build_measured_layout_bounds(
        cls,
        horizontal_bounds: typing.Sequence[tuple[float, float]],
        vertical_bounds: typing.Sequence[tuple[float, float]],
    ) -> layout_models.LayoutBounds:
        return layout_models.LayoutBounds(
            min_x=min(lower_bound for lower_bound, _ in horizontal_bounds),
            max_x=max(upper_bound for _, upper_bound in horizontal_bounds),
            min_y=min(lower_bound for lower_bound, _ in vertical_bounds),
            max_y=max(upper_bound for _, upper_bound in vertical_bounds),
        )

    @classmethod
    def build_folder_layout_source_data(
        cls, graph: nx.DiGraph
    ) -> internal_models.FolderLayoutSourceData:
        folder_to_nodes, root_folder_nodes = layout_ops.FolderDataOps.collect_folder_nodes(graph)
        folder_hierarchy = layout_ops.FolderDataOps.build_folder_hierarchy(folder_to_nodes)
        return internal_models.FolderLayoutSourceData(
            folder_to_nodes=folder_to_nodes,
            root_folder_nodes=root_folder_nodes,
            root_folders=folder_hierarchy[0],
            child_folders=folder_hierarchy[1],
        )

    @classmethod
    def build_folder_layouts(
        cls,
        source_data: internal_models.FolderLayoutSourceData,
        build_context: render_models.FolderLayoutBuildContext,
    ) -> dict[str, layout_models.ContainerLayout]:
        folder_layouts: dict[str, layout_models.ContainerLayout] = {}
        for folder_name in sorted(
            source_data.folder_to_nodes,
            key=layout_ops.SharedOps.folder_depth_sort_key,
            reverse=True,
        ):
            folder_layouts[folder_name] = _ContainerOps.build_folder_container_layout(
                folder_name,
                folder_layouts,
                build_context,
            )
        return folder_layouts

    @classmethod
    def build_constrained_layout_data(
        cls,
        graph: nx.DiGraph,
        node_visual_data: plot_types.NodeVisualDataMap,
    ) -> internal_models.ConstrainedLayoutData:
        source_data = cls.build_folder_layout_source_data(graph)
        layout_tuning = layout_ops.LocalSizingOps.build_layout_tuning(
            graph,
            source_data.folder_to_nodes,
        )
        build_context = render_models.FolderLayoutBuildContext(
            graph=graph,
            folder_to_nodes=source_data.folder_to_nodes,
            child_folders=source_data.child_folders,
            node_layout_k=CONSTANTS.default_node_layout_k,
            layout_tuning=layout_tuning,
            node_visual_data=node_visual_data,
        )
        return internal_models.ConstrainedLayoutData(
            source_data=source_data,
            build_context=build_context,
            folder_layouts=cls.build_folder_layouts(source_data, build_context),
        )

    @classmethod
    def build_folder_position_assignment(
        cls,
        folder_layouts: typing.Mapping[str, layout_models.ContainerLayout],
        final_positions: plot_types.LayoutPositionMap,
        layout_tuning: layout_models.LayoutTuning,
    ) -> render_models.FolderPositionAssignment:
        return render_models.FolderPositionAssignment(
            folder_layouts=folder_layouts,
            folder_rect_data=_AssignmentOps.build_folder_rect_data(),
            final_positions=final_positions,
            layout_tuning=layout_tuning,
        )


class _ConstrainedLayoutOps:
    @classmethod
    def assign_root_child_folder_positions(
        cls,
        root_layout: layout_models.ContainerLayout,
        assignment: render_models.FolderPositionAssignment,
    ) -> None:
        root_origin_x = -layout_ops.SharedOps.half(root_layout.width)
        root_origin_y = -layout_ops.SharedOps.half(root_layout.height)
        for folder_name in sorted(root_layout.child_origins):
            child_origin_x, child_origin_y = root_layout.child_origins[folder_name]
            _AssignmentOps.assign_folder_positions(
                folder_name,
                root_origin_x + child_origin_x,
                root_origin_y + child_origin_y,
                assignment,
            )

    @classmethod
    def create_constrained_layout(
        cls,
        graph: nx.DiGraph,
        node_visual_data: plot_types.NodeVisualDataMap,
    ) -> tuple[plot_types.LayoutPositionMap, contracts.FolderRectData]:
        constrained_layout_data = _BoundsOps.build_constrained_layout_data(graph, node_visual_data)
        root_layout = _AssignmentOps.build_root_container_layout(
            constrained_layout_data.source_data.root_folder_nodes,
            constrained_layout_data.source_data.root_folders,
            constrained_layout_data.folder_layouts,
            constrained_layout_data.build_context,
        )
        final_positions = layout_ops.NodeLayoutOps.build_root_final_positions(root_layout)
        assignment = _BoundsOps.build_folder_position_assignment(
            constrained_layout_data.folder_layouts,
            final_positions=final_positions,
            layout_tuning=constrained_layout_data.build_context.layout_tuning,
        )
        cls.assign_root_child_folder_positions(root_layout, assignment)
        return final_positions, assignment.folder_rect_data

    @classmethod
    def measure_layout_bounds(
        cls,
        final_positions: plot_types.LayoutPositionMap,
        folder_rect_data: contracts.FolderRectData,
        node_visual_data: plot_types.NodeVisualDataMap,
    ) -> layout_models.LayoutBounds:
        horizontal_bounds: list[tuple[float, float]] = []
        vertical_bounds: list[tuple[float, float]] = []
        _AssignmentOps.build_node_layout_bounds(
            final_positions,
            node_visual_data,
            horizontal_bounds,
            vertical_bounds,
        )
        _BoundsOps.build_folder_layout_bounds(
            folder_rect_data,
            horizontal_bounds,
            vertical_bounds,
        )
        if not horizontal_bounds or not vertical_bounds:
            return _BoundsOps.empty_layout_bounds()
        return _BoundsOps.build_measured_layout_bounds(horizontal_bounds, vertical_bounds)


class _PlotDimensionOps:
    @classmethod
    def build_plot_complexity_dimensions(
        cls,
        render_data: contracts.PreparedBokehRender,
    ) -> tuple[int, int]:
        node_count = len(render_data.final_positions)
        folder_count = render_data.folder_rect_data.folder_count
        max_node_size = max(
            (visual_data["viz_size"] for visual_data in render_data.node_visual_data.values()),
            default=CONSTANTS.min_node_size,
        )
        node_size_budget = max(max_node_size - CONSTANTS.min_node_size, 0)
        return (
            CONSTANTS.base_plot_width
            + max(node_count - CONSTANTS.plot_node_complexity_threshold, 0)
            * CONSTANTS.plot_width_node_step
            + max(folder_count - CONSTANTS.plot_folder_complexity_threshold, 0)
            * CONSTANTS.plot_width_folder_step
            + node_size_budget * CONSTANTS.plot_width_node_size_step,
            CONSTANTS.base_plot_height
            + max(node_count - CONSTANTS.plot_node_complexity_threshold, 0)
            * CONSTANTS.plot_height_node_step
            + max(folder_count - CONSTANTS.plot_folder_complexity_threshold, 0)
            * CONSTANTS.plot_height_folder_step
            + node_size_budget * CONSTANTS.plot_height_node_size_step,
        )

    @classmethod
    def build_plot_dimensions(
        cls,
        render_data: contracts.PreparedBokehRender,
    ) -> layout_models.PlotDimensions:
        layout_bounds = _ConstrainedLayoutOps.measure_layout_bounds(
            render_data.final_positions,
            render_data.folder_rect_data,
            render_data.node_visual_data,
        )
        complexity_width, complexity_height = cls.build_plot_complexity_dimensions(render_data)
        width = math.ceil(
            layout_ops.NodeSizeOps.clamp_float(
                max(
                    layout_bounds.width * CONSTANTS.plot_pixels_per_layout_unit,
                    float(complexity_width),
                ),
                CONSTANTS.base_plot_width,
                CONSTANTS.max_plot_width,
            )
        )
        height = math.ceil(
            layout_ops.NodeSizeOps.clamp_float(
                max(
                    layout_bounds.height * CONSTANTS.plot_pixels_per_layout_unit,
                    float(complexity_height),
                ),
                CONSTANTS.base_plot_height,
                CONSTANTS.max_plot_height,
            )
        )
        return layout_models.PlotDimensions(width=width, height=height)

    @classmethod
    def build_empty_plot_ranges(cls) -> tuple[bokeh_models.Range1d, bokeh_models.Range1d]:
        return (
            bokeh_models.Range1d(
                start=-CONSTANTS.empty_plot_range_extent,
                end=CONSTANTS.empty_plot_range_extent,
            ),
            bokeh_models.Range1d(
                start=-CONSTANTS.empty_plot_range_extent,
                end=CONSTANTS.empty_plot_range_extent,
            ),
        )

    @classmethod
    def build_padded_layout_size(
        cls,
        layout_bounds: layout_models.LayoutBounds,
    ) -> render_models.PaddedLayoutSize:
        padding_x = max(
            CONSTANTS.initial_view_min_padding_units,
            CONSTANTS.layout_viewport_padding_units,
            layout_bounds.width * CONSTANTS.initial_view_padding_fraction,
        )
        padding_y = max(
            CONSTANTS.initial_view_min_padding_units,
            CONSTANTS.layout_viewport_padding_units,
            layout_bounds.height * CONSTANTS.initial_view_padding_fraction,
        )
        return render_models.PaddedLayoutSize(
            width=max(
                layout_bounds.width + CONSTANTS.layout_position_padding_multiplier * padding_x,
                1.0,
            ),
            height=max(
                layout_bounds.height + CONSTANTS.layout_position_padding_multiplier * padding_y,
                1.0,
            ),
        )

    @classmethod
    def build_plot_view_half_spans(
        cls,
        padded_layout_size: render_models.PaddedLayoutSize,
        plot_dimensions: layout_models.PlotDimensions,
    ) -> tuple[float, float]:
        plot_aspect_ratio = max(
            float(plot_dimensions.width) / max(float(plot_dimensions.height), 1.0),
            CONSTANTS.min_plot_aspect_ratio,
        )
        if padded_layout_size.width / padded_layout_size.height > plot_aspect_ratio:
            return (
                layout_ops.SharedOps.half(padded_layout_size.width)
                * CONSTANTS.initial_view_safety_scale,
                layout_ops.SharedOps.half(padded_layout_size.width / plot_aspect_ratio)
                * CONSTANTS.initial_view_safety_scale,
            )
        return (
            layout_ops.SharedOps.half(padded_layout_size.height * plot_aspect_ratio)
            * CONSTANTS.initial_view_safety_scale,
            layout_ops.SharedOps.half(padded_layout_size.height)
            * CONSTANTS.initial_view_safety_scale,
        )

    @classmethod
    def build_layout_center(
        cls,
        layout_bounds: layout_models.LayoutBounds,
    ) -> tuple[float, float]:
        return (
            layout_ops.SharedOps.half(layout_bounds.min_x + layout_bounds.max_x),
            layout_ops.SharedOps.half(layout_bounds.min_y + layout_bounds.max_y),
        )

    @classmethod
    def build_centered_plot_ranges(
        cls,
        layout_bounds: layout_models.LayoutBounds,
        padded_layout_size: render_models.PaddedLayoutSize,
        plot_dimensions: layout_models.PlotDimensions,
    ) -> tuple[bokeh_models.Range1d, bokeh_models.Range1d]:
        center_position = cls.build_layout_center(layout_bounds)
        half_spans = cls.build_plot_view_half_spans(padded_layout_size, plot_dimensions)
        return (
            bokeh_models.Range1d(
                start=center_position[0] - half_spans[0],
                end=center_position[0] + half_spans[0],
            ),
            bokeh_models.Range1d(
                start=center_position[1] - half_spans[1],
                end=center_position[1] + half_spans[1],
            ),
        )


class _PlotRangeOps:
    @classmethod
    def build_plot_ranges(
        cls,
        render_data: contracts.PreparedBokehRender,
        plot_dimensions: layout_models.PlotDimensions,
    ) -> tuple[bokeh_models.Range1d, bokeh_models.Range1d]:
        layout_bounds = _ConstrainedLayoutOps.measure_layout_bounds(
            render_data.final_positions,
            render_data.folder_rect_data,
            render_data.node_visual_data,
        )
        if not layout_bounds.width and not layout_bounds.height:
            return _PlotDimensionOps.build_empty_plot_ranges()
        return _PlotDimensionOps.build_centered_plot_ranges(
            layout_bounds,
            _PlotDimensionOps.build_padded_layout_size(layout_bounds),
            plot_dimensions,
        )

    @classmethod
    def build_bokeh_layout(
        cls,
        graph: nx.DiGraph,
        layout: str,
        node_visual_data: plot_types.NodeVisualDataMap,
    ) -> tuple[plot_types.LayoutPositionMap, contracts.FolderRectData]:
        if layout != "constrained":
            raise ValueError(
                f"Unsupported Bokeh layout '{layout}'. Supported layouts: constrained."
            )
        return _ConstrainedLayoutOps.create_constrained_layout(graph, node_visual_data)


# Backward-compatible public aliases preserved for existing imports and intra-package access.
SectionOps = _SectionOps
ContainerOps = _ContainerOps
AssignmentOps = _AssignmentOps
BoundsOps = _BoundsOps
ConstrainedLayoutOps = _ConstrainedLayoutOps
PlotDimensionOps = _PlotDimensionOps
PlotRangeOps = _PlotRangeOps
