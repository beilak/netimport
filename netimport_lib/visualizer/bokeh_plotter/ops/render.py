"""Bokeh plot and renderer helpers for the visualizer."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, Protocol, cast

import networkx as nx
from bokeh import models as bokeh_models
from bokeh import plotting as bokeh_plotting

from netimport_lib.visualizer.bokeh_plotter import contracts
from netimport_lib.visualizer.bokeh_plotter.constants import CONSTANTS
from netimport_lib.visualizer.bokeh_plotter.models import render as render_models
from netimport_lib.visualizer.bokeh_plotter.ops import layout as layout_ops
from netimport_lib.visualizer.bokeh_plotter.ops import structure as structure_ops


if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from netimport_lib.visualizer.bokeh_plotter.models.internal import (
        BokehRendererLayer,
        GraphRendererLike,
    )


_BOKEH_MODELS_ANY = cast("Any", bokeh_models)


class _PlotDimensionsLike(Protocol):
    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...


class _GraphVisualOps:
    @classmethod
    def build_node_visual_data(
        cls,
        graph: nx.DiGraph,
    ) -> dict[object, contracts.NodeVisualData]:
        degrees = dict(graph.degree())
        node_count = graph.number_of_nodes()
        visual_data: dict[object, contracts.NodeVisualData] = {}

        for node_id in sorted(graph.nodes(), key=str):
            visual_data[node_id] = cls.build_single_node_visual_data(
                graph.nodes[node_id],
                node_id,
                degrees.get(node_id, 0),
                node_count,
            )

        return visual_data

    @classmethod
    def build_single_node_visual_data(
        cls,
        node_data: Mapping[str, object],
        node_id: object,
        current_degree: int,
        node_count: int,
    ) -> contracts.NodeVisualData:
        calculated_size = layout_ops.NodeSizeOps.calculate_node_visual_size(
            current_degree,
            node_count,
        )
        return contracts.NodeVisualData(
            viz_size=calculated_size,
            viz_color=CONSTANTS.color_map.get(
                str(node_data.get("type", "unresolved")),
                CONSTANTS.default_node_color,
            ),
            viz_label=str(node_data.get("label", node_id)),
            viz_degree=current_degree,
            viz_type=str(node_data.get("type", "unresolved")),
            viz_label_y_offset=int(
                layout_ops.SharedOps.half(float(calculated_size)) + CONSTANTS.label_padding
            ),
            in_degree=layout_ops.SharedOps.to_int(node_data.get("in_degree", 0)),
            out_degree=layout_ops.SharedOps.to_int(node_data.get("out_degree", 0)),
            total_degree=layout_ops.SharedOps.to_int(node_data.get("total_degree", 0)),
        )

    @classmethod
    def copy_sorted_graph_structure(cls, graph: nx.DiGraph) -> nx.DiGraph:
        graph_to_draw = nx.DiGraph()
        for node_id, node_data in sorted(
            graph.nodes(data=True),
            key=layout_ops.SharedOps.node_item_sort_key,
        ):
            graph_to_draw.add_node(node_id, **dict(node_data))
        for start_node, end_node in sorted(
            graph.edges(),
            key=layout_ops.SharedOps.edge_sort_key,
        ):
            graph_to_draw.add_edge(start_node, end_node)
        return graph_to_draw

    @classmethod
    def copy_graph_with_visual_data(
        cls,
        graph: nx.DiGraph,
        node_visual_data: Mapping[object, contracts.NodeVisualData],
    ) -> nx.DiGraph:
        graph_to_draw = cls.copy_sorted_graph_structure(graph)
        for node_id, visual_data in node_visual_data.items():
            graph_to_draw.nodes[node_id].update(visual_data)
        return graph_to_draw

    @classmethod
    def build_edge_visual_style(cls, graph: nx.DiGraph) -> render_models.EdgeVisualStyle:
        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()
        if (
            node_count >= CONSTANTS.compact_graph_node_count_threshold
            or edge_count >= CONSTANTS.compact_edge_count_threshold
        ):
            return CONSTANTS.compact_edge_style
        if (
            node_count >= CONSTANTS.medium_graph_node_count_threshold
            or edge_count >= CONSTANTS.medium_edge_count_threshold
        ):
            return CONSTANTS.medium_edge_style
        return CONSTANTS.default_edge_style

    @classmethod
    def build_render_policy(cls, graph: nx.DiGraph) -> render_models.RenderPolicy:
        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()
        dense_graph = (
            node_count >= CONSTANTS.lod_render_node_threshold
            or edge_count >= CONSTANTS.lod_render_edge_threshold
        )
        return render_models.RenderPolicy(
            output_backend="canvas",
            show_arrows=not (
                node_count >= CONSTANTS.arrow_render_node_threshold
                or edge_count >= CONSTANTS.arrow_render_edge_threshold
            ),
            lod_threshold=1 if dense_graph else None,
            lod_factor=CONSTANTS.lod_factor,
            lod_interval=CONSTANTS.lod_interval_ms,
            lod_timeout=CONSTANTS.lod_timeout_ms,
        )


class _PlotOps:
    @classmethod
    def build_toolbar_stylesheet(cls) -> bokeh_models.InlineStyleSheet:
        icon_scale = (
            f"{CONSTANTS.toolbar_icon_scale_percent}% {CONSTANTS.toolbar_icon_scale_percent}%"
        )
        return bokeh_models.InlineStyleSheet(
            css=(
                ":host {"
                f" --button-width: {CONSTANTS.toolbar_button_width_px}px;"
                f" --button-height: {CONSTANTS.toolbar_button_height_px}px;"
                " position: fixed;"
                f" left: {CONSTANTS.toolbar_viewport_left_px}px;"
                f" top: {CONSTANTS.toolbar_viewport_top_px}px;"
                " z-index: 1000;"
                " padding: 6px;"
                " border-radius: 12px;"
                " border: 1px solid rgba(15, 23, 42, 0.14);"
                " background: rgba(255, 255, 255, 0.94);"
                " box-shadow: 0 12px 28px rgba(15, 23, 42, 0.18);"
                " backdrop-filter: blur(8px);"
                " }"
                " .bk-tool-icon {"
                f" mask-size: {icon_scale};"
                f" -webkit-mask-size: {icon_scale};"
                f" background-size: {icon_scale};"
                " }"
                " .bk-divider {"
                " opacity: 0.35;"
                " }"
            )
        )

    @classmethod
    def configure_plot_tools(
        cls,
        plot: bokeh_plotting.figure,
    ) -> tuple[bokeh_models.PanTool, bokeh_models.HoverTool]:
        pan_tool = bokeh_models.PanTool()
        hover_tool = bokeh_models.HoverTool(visible=False)
        plot.add_tools(
            pan_tool,
            bokeh_models.WheelZoomTool(maintain_focus=False, visible=False),
            bokeh_models.ZoomInTool(),
            bokeh_models.ZoomOutTool(),
            bokeh_models.BoxZoomTool(),
            bokeh_models.ResetTool(),
            bokeh_models.SaveTool(),
            bokeh_models.TapTool(visible=False),
            hover_tool,
        )
        return pan_tool, hover_tool

    @classmethod
    def add_folder_overlays(
        cls,
        plot: bokeh_plotting.figure,
        folder_rect_data: contracts.FolderRectData,
    ) -> bokeh_models.ColumnDataSource:
        folder_source = bokeh_models.ColumnDataSource(data=folder_rect_data.as_column_data())
        plot.rect(
            x=CONSTANTS.folder_x_field,
            y=CONSTANTS.folder_y_field,
            width=CONSTANTS.folder_width_field,
            height=CONSTANTS.folder_height_field,
            source=folder_source,
            fill_color=CONSTANTS.folder_color_field,
            fill_alpha=CONSTANTS.folder_rect_fill_alpha,
            line_color=CONSTANTS.black_color,
            line_dash="dashed",
            level="underlay",
        )
        plot.add_layout(
            _BOKEH_MODELS_ANY.LabelSet(
                x=CONSTANTS.folder_x_field,
                y=CONSTANTS.folder_label_y_field,
                text=CONSTANTS.folder_name_field,
                source=folder_source,
                text_font_size="12pt",
                text_color=CONSTANTS.black_color,
                text_align="center",
                y_offset=0,
                level="overlay",
            )
        )
        return folder_source

    @classmethod
    def create_bokeh_plot(
        cls,
        folder_rect_data: contracts.FolderRectData,
        plot_dimensions: _PlotDimensionsLike,
        plot_ranges: tuple[bokeh_models.Range1d, bokeh_models.Range1d],
        render_policy: render_models.RenderPolicy,
    ) -> tuple[bokeh_plotting.figure, bokeh_models.ColumnDataSource]:
        plot = bokeh_plotting.figure(title=CONSTANTS.interactive_plot_title)
        plot.output_backend = render_policy.output_backend
        plot.width = plot_dimensions.width
        plot.height = plot_dimensions.height
        plot.x_range = plot_ranges[0]
        plot.y_range = plot_ranges[1]
        plot.toolbar_location = "left"
        plot.toolbar_inner = True
        plot.toolbar_sticky = True
        plot.toolbar.tools = []
        plot.toolbar.logo = None
        plot.toolbar.autohide = False
        plot.toolbar.stylesheets = [cls.build_toolbar_stylesheet()]
        plot.match_aspect = True
        plot.lod_threshold = render_policy.lod_threshold
        plot.lod_factor = render_policy.lod_factor
        plot.lod_interval = render_policy.lod_interval
        plot.lod_timeout = render_policy.lod_timeout

        pan_tool, hover_tool = cls.configure_plot_tools(plot)
        plot.toolbar.active_drag = pan_tool
        plot.toolbar.active_inspect = hover_tool
        return plot, cls.add_folder_overlays(plot, folder_rect_data)

    @classmethod
    def build_plot_for_render(
        cls,
        render_data: contracts.PreparedBokehRender,
        render_policy: render_models.RenderPolicy,
    ) -> bokeh_plotting.figure:
        plot_dimensions = structure_ops.PlotDimensionOps.build_plot_dimensions(render_data)
        plot, _folder_source = cls.create_bokeh_plot(
            render_data.folder_rect_data,
            plot_dimensions,
            structure_ops.PlotRangeOps.build_plot_ranges(render_data, plot_dimensions),
            render_policy,
        )
        return plot

    @classmethod
    def configure_hover(
        cls,
        plot: bokeh_plotting.figure,
        graph_renderer: GraphRendererLike,
    ) -> None:
        hover_tool = cast(
            "bokeh_models.HoverTool | None",
            plot.select_one({"type": bokeh_models.HoverTool}),
        )
        if hover_tool is None:
            return

        hover_renderer = cast("Any", graph_renderer.node_renderer)
        hover_tool.renderers = [hover_renderer]
        hover_tool.tooltips = [
            ("Name", "@viz_label"),
            ("Type", "@viz_type"),
            ("Total Links", "@total_degree"),
            ("Incoming", "@in_degree"),
            ("Outgoing", "@out_degree"),
            ("ID", "@index"),
            ("Folder", "@folder"),
        ]


class _RendererSyncOps:
    @classmethod
    def get_graph_renderer_node_data(
        cls,
        graph_renderer: GraphRendererLike,
    ) -> Mapping[str, object]:
        node_renderer = cast("BokehRendererLayer", graph_renderer.node_renderer)
        data_source = node_renderer.data_source
        return cast("Mapping[str, object]", data_source.data)

    @classmethod
    def build_ordered_renderer_node_ids(
        cls,
        node_data: Mapping[str, object],
    ) -> list[str] | None:
        indices = node_data.get("index")
        if not isinstance(indices, list) or not indices:
            return None
        return [str(node_id) for node_id in indices]

    @classmethod
    def apply_synced_node_coordinates(
        cls,
        node_data: Mapping[str, object],
        synced_coordinates: tuple[list[float], list[float]],
    ) -> None:
        node_xs, node_ys = synced_coordinates
        mutable_node_data = cast("dict[str, object]", node_data)
        mutable_node_data["x"] = node_xs
        mutable_node_data["y"] = node_ys

    @classmethod
    def sync_node_coordinates(
        cls,
        graph_renderer: GraphRendererLike,
        final_positions: dict[str, tuple[float, float]],
    ) -> None:
        node_data = cls.get_graph_renderer_node_data(graph_renderer)
        if cls.node_coordinates_are_already_synced(node_data):
            return

        ordered_node_ids = cls.build_ordered_renderer_node_ids(node_data)
        if ordered_node_ids is None:
            return
        synced_coordinates = cls.build_synced_node_coordinates(ordered_node_ids, final_positions)
        if synced_coordinates is None:
            return
        cls.apply_synced_node_coordinates(node_data, synced_coordinates)

    @classmethod
    def configure_node_renderer(
        cls,
        graph_renderer: GraphRendererLike,
    ) -> None:
        node_renderer = cast("BokehRendererLayer", graph_renderer.node_renderer)
        node_renderer.glyph = bokeh_models.Scatter(
            marker="circle",
            size=CONSTANTS.viz_size_field,
            fill_color="viz_color",
            fill_alpha=CONSTANTS.node_fill_alpha,
            line_color=CONSTANTS.black_color,
            line_width=0.5,
        )
        node_renderer.hover_glyph = bokeh_models.Scatter(
            marker="circle",
            size=CONSTANTS.viz_size_field,
            fill_color="orange",
            fill_alpha=CONSTANTS.node_fill_alpha,
            line_color=CONSTANTS.black_color,
            line_width=2,
        )
        node_renderer.selection_glyph = bokeh_models.Scatter(
            marker="circle",
            size=CONSTANTS.viz_size_field,
            fill_color="firebrick",
            fill_alpha=CONSTANTS.node_fill_alpha,
            line_color=CONSTANTS.black_color,
            line_width=2,
        )

    @classmethod
    def node_coordinates_are_already_synced(
        cls,
        node_data: Mapping[str, object],
    ) -> bool:
        return isinstance(node_data.get(CONSTANTS.folder_x_field), list) and isinstance(
            node_data.get(CONSTANTS.folder_y_field),
            list,
        )

    @classmethod
    def build_synced_node_coordinates(
        cls,
        ordered_node_ids: Sequence[str],
        final_positions: dict[str, tuple[float, float]],
    ) -> tuple[list[float], list[float]] | None:
        try:
            return (
                [final_positions[node_id][0] for node_id in ordered_node_ids],
                [final_positions[node_id][1] for node_id in ordered_node_ids],
            )
        except KeyError:
            return None


class _EdgeRenderOps:
    @classmethod
    def configure_edge_renderer(
        cls,
        graph_renderer: GraphRendererLike,
        edge_style: render_models.EdgeVisualStyle,
    ) -> None:
        edge_renderer = cast("BokehRendererLayer", graph_renderer.edge_renderer)
        edge_renderer.glyph = bokeh_models.MultiLine(
            line_color="#CCCCCC",
            line_alpha=edge_style.line_alpha,
            line_width=edge_style.line_width,
        )
        edge_renderer.hover_glyph = bokeh_models.MultiLine(
            line_color="orange",
            line_alpha=CONSTANTS.edge_hover_line_alpha,
            line_width=2,
        )
        edge_renderer.selection_glyph = bokeh_models.MultiLine(
            line_color="firebrick",
            line_alpha=CONSTANTS.edge_selection_line_alpha,
            line_width=2,
        )

    @classmethod
    def append_arrow_coordinates(
        cls,
        arrow_source_data: contracts.ArrowSourceData,
        final_positions: dict[str, tuple[float, float]],
        start_node: str,
        end_node: str,
    ) -> None:
        start_coords = final_positions[start_node]
        end_coords = final_positions[end_node]
        arrow_source_data["start_x"].append(start_coords[0])
        arrow_source_data["start_y"].append(start_coords[1])
        arrow_source_data["end_x"].append(end_coords[0])
        arrow_source_data["end_y"].append(end_coords[1])

    @classmethod
    def build_arrow_source_data(
        cls,
        graph: nx.DiGraph,
        final_positions: dict[str, tuple[float, float]],
    ) -> contracts.ArrowSourceData:
        arrow_source_data: contracts.ArrowSourceData = {
            "start_x": [],
            "start_y": [],
            "end_x": [],
            "end_y": [],
        }
        for start_node, end_node in sorted(
            graph.edges(),
            key=layout_ops.SharedOps.edge_sort_key,
        ):
            cls.append_arrow_coordinates(
                arrow_source_data,
                final_positions,
                str(start_node),
                str(end_node),
            )

        return arrow_source_data

    @classmethod
    def add_arrow_renderer(
        cls,
        plot: bokeh_plotting.figure,
        arrow_source_data: contracts.ArrowSourceData,
        edge_style: render_models.EdgeVisualStyle,
    ) -> None:
        arrow_source = bokeh_models.ColumnDataSource(data=arrow_source_data)
        arrow_renderer = _BOKEH_MODELS_ANY.Arrow(
            end=_BOKEH_MODELS_ANY.OpenHead(
                line_color="gray",
                line_alpha=edge_style.arrow_alpha,
                line_width=edge_style.arrow_line_width,
                size=edge_style.arrow_head_size,
            ),
            source=arrow_source,
            x_start="start_x",
            y_start="start_y",
            x_end="end_x",
            y_end="end_y",
        )
        arrow_renderer.line_alpha = edge_style.arrow_alpha
        arrow_renderer.line_width = edge_style.arrow_line_width
        plot.add_layout(arrow_renderer)

    @classmethod
    def render_graph_on_plot(
        cls,
        graph_to_draw: nx.DiGraph,
        render_data: contracts.PreparedBokehRender,
        edge_style: render_models.EdgeVisualStyle,
        plot: bokeh_plotting.figure,
        *,
        show_arrows: bool,
    ) -> None:
        graph_renderer = bokeh_plotting.from_networkx(
            graph_to_draw,
            cast("dict[int | str, Sequence[float]]", render_data.final_positions),
        )
        _RendererSyncOps.sync_node_coordinates(graph_renderer, render_data.final_positions)
        _RendererSyncOps.configure_node_renderer(graph_renderer)
        cls.configure_edge_renderer(graph_renderer, edge_style)
        if show_arrows:
            cls.add_arrow_renderer(plot, render_data.arrow_source_data, edge_style)
        graph_renderer.selection_policy = bokeh_models.NodesAndLinkedEdges()
        graph_renderer.inspection_policy = bokeh_models.NodesAndLinkedEdges()
        _PlotOps.configure_hover(plot, graph_renderer)
        plot.renderers.append(graph_renderer)


# Backward-compatible public aliases preserved for existing imports and intra-package access.
GraphVisualOps = _GraphVisualOps
PlotOps = _PlotOps
RendererSyncOps = _RendererSyncOps
EdgeRenderOps = _EdgeRenderOps
