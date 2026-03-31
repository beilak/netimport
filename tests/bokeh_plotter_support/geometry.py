from netimport_lib.visualizer import bokeh_plotter
from tests.bokeh_plotter_support.rendering import half


def build_rect_map(
    folder_rect_data: "bokeh_plotter.FolderRectData",
) -> dict[str, tuple[float, float, float, float]]:
    return {
        name: (x_coord, y_coord, width, height)
        for name, x_coord, y_coord, width, height in zip(
            folder_rect_data["name"],
            folder_rect_data["x"],
            folder_rect_data["y"],
            folder_rect_data["width"],
            folder_rect_data["height"],
            strict=True,
        )
    }


def point_is_inside_rect(
    x_coord: float,
    y_coord: float,
    rect: tuple[float, float, float, float],
    *,
    margin: float = bokeh_plotter.ZERO_FLOAT,
) -> bool:
    rect_x, rect_y, rect_width, rect_height = rect
    return (
        abs(x_coord - rect_x) <= half(rect_width) - margin
        and abs(y_coord - rect_y) <= half(rect_height) - margin
    )


def node_radius(
    render_data: bokeh_plotter.PreparedBokehRender,
    node_id: str,
) -> float:
    return node_visual_size(render_data, node_id) / bokeh_plotter.PLOT_PIXELS_PER_LAYOUT_UNIT / 2


def node_visual_size(
    render_data: bokeh_plotter.PreparedBokehRender,
    node_id: str,
) -> int:
    return render_data.node_visual_data[node_id]["viz_size"]


def node_visual_fits_inside_rect(
    node_id: str,
    render_data: bokeh_plotter.PreparedBokehRender,
    rect: tuple[float, float, float, float],
) -> bool:
    node_x, node_y = render_data.final_positions[node_id]
    return point_is_inside_rect(
        node_x,
        node_y,
        rect,
        margin=node_radius(render_data, node_id),
    )


def rect_bounds(rect: tuple[float, ...]) -> tuple[float, float, float, float]:
    rect_x, rect_y, rect_width, rect_height = rect
    return (
        rect_x - half(rect_width),
        rect_x + half(rect_width),
        rect_y - half(rect_height),
        rect_y + half(rect_height),
    )


def node_bounds(
    render_data: bokeh_plotter.PreparedBokehRender,
    node_id: str,
    position: tuple[float, float],
) -> tuple[float, float, float, float]:
    x_coord, y_coord = position
    radius = node_radius(render_data, node_id)
    return (
        x_coord - radius,
        x_coord + radius,
        y_coord - radius,
        y_coord + radius,
    )
