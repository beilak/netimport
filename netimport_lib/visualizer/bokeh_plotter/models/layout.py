"""Layout data models for the Bokeh visualizer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocalNodeLayout:
    """Relative node placement within a container block."""

    width: float
    height: float
    positions: dict[str, tuple[float, float]]


@dataclass(frozen=True, slots=True)
class PackedBoxLayout:
    """Packed child-box placement within a container block."""

    width: float
    height: float
    origins: dict[str, tuple[float, float]]


@dataclass(frozen=True, slots=True)
class ContainerLayout:
    """Computed box geometry for a folder or synthetic root container."""

    width: float
    height: float
    node_positions: dict[str, tuple[float, float]]
    child_origins: dict[str, tuple[float, float]]


@dataclass(frozen=True, slots=True)
class LayoutTuning:
    """Adaptive spacing values for constrained layout."""

    min_node_block_span: float
    node_block_cell_span: float
    node_layout_inset: float
    folder_padding_x: float
    folder_padding_y: float
    folder_label_height: float
    folder_section_gap: float
    folder_grid_gap_x: float
    folder_grid_gap_y: float
    root_section_gap: float
    min_folder_content_width: float
    min_folder_content_height: float


@dataclass(frozen=True, slots=True)
class PlotDimensions:
    """Pixel dimensions for the rendered Bokeh plot."""

    width: int
    height: int


@dataclass(frozen=True, slots=True)
class LayoutBounds:
    """Measured layout extents in data coordinates."""

    min_x: float
    max_x: float
    min_y: float
    max_y: float

    @property
    def width(self) -> float:
        """Return the horizontal span of the measured bounds."""
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        """Return the vertical span of the measured bounds."""
        return self.max_y - self.min_y
