"""Public contracts for Bokeh graph rendering."""

from dataclasses import dataclass, field
from functools import lru_cache
from importlib import import_module
from typing import Literal, Protocol, TypeAlias, TypedDict, cast, overload

from netimport_lib.visualizer.bokeh_plotter.models.layout import (
    ContainerLayout,
    LayoutTuning,
)


class _BokehPlotterConstantsLike(Protocol):
    """Runtime view of the subset of shared constants used by the contracts module."""

    half_divisor: float
    folder_rect_fill_color: str
    folder_x_field: str
    folder_y_field: str
    folder_label_y_field: str
    folder_width_field: str
    folder_height_field: str
    folder_name_field: str
    folder_color_field: str


@lru_cache(maxsize=1)
def _get_constants() -> _BokehPlotterConstantsLike:
    """Load shared Bokeh constants lazily to avoid the contracts/constants import cycle."""
    constants_module = import_module("netimport_lib.visualizer.bokeh_plotter.constants")
    return cast("_BokehPlotterConstantsLike", constants_module.CONSTANTS)


class ArrowSourceData(TypedDict):
    """Arrow renderer coordinates."""

    start_x: list[float]
    start_y: list[float]
    end_x: list[float]
    end_y: list[float]


class NodeVisualData(TypedDict):
    """Visual attributes derived from graph metadata."""

    viz_size: int
    viz_color: str
    viz_label: str
    viz_degree: int
    viz_type: str
    viz_label_y_offset: int
    in_degree: int
    out_degree: int
    total_degree: int


FolderRectDataSource: TypeAlias = dict[str, list[float] | list[str]]


@dataclass(slots=True)
class FolderRectData:
    """Column-oriented folder rectangle data for Bokeh."""

    center_xs: list[float] = field(default_factory=list)
    center_ys: list[float] = field(default_factory=list)
    label_ys: list[float] = field(default_factory=list)
    widths: list[float] = field(default_factory=list)
    heights: list[float] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)

    @property
    def folder_count(self) -> int:
        """Return the total number of recorded folder rectangles."""
        return len(self.names)

    def append_folder(
        self,
        folder_name: str,
        origin_x: float,
        origin_y: float,
        layout: ContainerLayout,
        layout_tuning: LayoutTuning,
    ) -> None:
        """Append a folder rectangle and label placement."""
        constants = _get_constants()

        self.center_xs.append(origin_x + layout.width / constants.half_divisor)
        self.center_ys.append(origin_y + layout.height / constants.half_divisor)
        self.label_ys.append(
            origin_y
            + layout.height
            - layout_tuning.folder_padding_y
            - layout_tuning.folder_label_height / constants.half_divisor
        )
        self.widths.append(layout.width)
        self.heights.append(layout.height)
        self.names.append(folder_name.rsplit("/", maxsplit=1)[-1])
        self.colors.append(constants.folder_rect_fill_color)

    @overload
    def __getitem__(
        self,
        field_name: Literal["x", "y", "label_y", "width", "height"],
    ) -> list[float]: ...

    @overload
    def __getitem__(self, field_name: Literal["name", "color"]) -> list[str]: ...

    def __getitem__(self, field_name: str) -> list[float] | list[str]:
        """Provide backwards-compatible dict-style access for tests and callers."""
        return self.as_column_data()[field_name]

    def __eq__(self, other: object) -> bool:
        """Keep comparisons compatible with the legacy dict payload shape."""
        if isinstance(other, FolderRectData):
            return self.as_column_data() == other.as_column_data()
        if isinstance(other, dict):
            return self.as_column_data() == other
        return False

    def __hash__(self) -> int:
        """Hash the column payload so the custom equality stays well-defined."""
        return hash(
            (
                tuple(self.center_xs),
                tuple(self.center_ys),
                tuple(self.label_ys),
                tuple(self.widths),
                tuple(self.heights),
                tuple(self.names),
                tuple(self.colors),
            ),
        )

    def as_column_data(self) -> FolderRectDataSource:
        """Return the Bokeh ``ColumnDataSource`` payload."""
        constants = _get_constants()

        return {
            constants.folder_x_field: self.center_xs,
            constants.folder_y_field: self.center_ys,
            constants.folder_label_y_field: self.label_ys,
            constants.folder_width_field: self.widths,
            constants.folder_height_field: self.heights,
            constants.folder_name_field: self.names,
            constants.folder_color_field: self.colors,
        }


@dataclass(frozen=True, slots=True)
class PreparedBokehRender:
    """Data prepared for Bokeh rendering."""

    final_positions: dict[str, tuple[float, float]]
    folder_rect_data: FolderRectData
    arrow_source_data: ArrowSourceData
    node_visual_data: dict[object, NodeVisualData]
