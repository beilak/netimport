from collections.abc import Callable

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import plotly.graph_objects as go

from netimport_lib.visualizer.bokeh_plotter import draw_bokeh_graph
from netimport_lib.visualizer.bokeh_plotter_v2 import draw_bokeh_graph
from netimport_lib.visualizer.mpl_plotter import draw_graph_mpl


GRAPH_VISUALIZERS: dict[str, Callable] = {
    "bokeh": draw_bokeh_graph,
    "mpl": draw_graph_mpl,
}
