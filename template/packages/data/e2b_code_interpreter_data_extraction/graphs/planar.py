from datetime import date
from typing import List, Tuple, Union, Sequence, Any, Literal

import matplotlib
import numpy
from matplotlib.axes import Axes
from matplotlib.dates import _SwitchableDateConverter
from pydantic import BaseModel, field_validator, Field

from .base import Graph2D, GraphType
from ..utils.filtering import is_grid_line


class PointData(BaseModel):
    label: str
    points: List[Tuple[Union[str, float], Union[str, float]]]

    @field_validator("points", mode="before")
    @classmethod
    def transform_points(
        cls, value
    ) -> List[Tuple[Union[str, float], Union[str, float]]]:
        parsed_value = []
        for x, y in value:
            if isinstance(x, date):
                x = x.isoformat()
            if isinstance(x, numpy.datetime64):
                x = x.astype("datetime64[s]").astype(str)

            if isinstance(y, date):
                y = y.isoformat()
            if isinstance(y, numpy.datetime64):
                y = y.astype("datetime64[s]").astype(str)

            parsed_value.append((x, y))
        return parsed_value


class PointGraph(Graph2D):
    x_ticks: List[Union[str, float]] = Field(default_factory=list)
    x_tick_labels: List[str] = Field(default_factory=list)
    x_scale: str = Field(default="linear")

    y_ticks: List[Union[str, float]] = Field(default_factory=list)
    y_tick_labels: List[str] = Field(default_factory=list)
    y_scale: str = Field(default="linear")

    elements: List[PointData] = Field(default_factory=list)

    def _extract_info(self, ax: Axes) -> None:
        """
        Function to extract information for PointGraph
        """
        super()._extract_info(ax)

        self.x_tick_labels = [label.get_text() for label in ax.get_xticklabels()]

        x_ticks = ax.get_xticks()
        self.x_ticks = self._extract_ticks_info(ax.xaxis.converter, x_ticks)
        self.x_scale = self._detect_scale(
            ax.xaxis.converter, ax.get_xscale(), self.x_ticks, self.x_tick_labels
        )

        self.y_tick_labels = [label.get_text() for label in ax.get_yticklabels()]
        self.y_ticks = self._extract_ticks_info(ax.yaxis.converter, ax.get_yticks())
        self.y_scale = self._detect_scale(
            ax.yaxis.converter, ax.get_yscale(), self.y_ticks, self.y_tick_labels
        )

    @staticmethod
    def _detect_scale(converter, scale: str, ticks: Sequence, labels: Sequence) -> str:
        # If the converter is a date converter, it's a datetime scale
        if isinstance(converter, _SwitchableDateConverter):
            return "datetime"

        # If the scale is not linear, it can't be categorical
        if scale != "linear":
            return scale

        # If all the ticks are integers and are in order from 0 to n-1
        # and the labels aren't corresponding to the ticks, it's categorical
        for i, tick_and_label in enumerate(zip(ticks, labels)):
            tick, label = tick_and_label
            if isinstance(tick, (int, float)) and tick == i and str(i) != label:
                continue
            # Found a tick, which wouldn't be in a categorical scale
            return "linear"

        return "categorical"

    @staticmethod
    def _extract_ticks_info(converter: Any, ticks: Sequence) -> list:
        if isinstance(converter, _SwitchableDateConverter):
            return [matplotlib.dates.num2date(tick).isoformat() for tick in ticks]
        else:
            example_tick = ticks[0]

            if isinstance(example_tick, (int, float)):
                return [float(tick) for tick in ticks]
            else:
                return list(ticks)


class LineGraph(PointGraph):
    type: Literal[GraphType.LINE] = GraphType.LINE

    def _extract_info(self, ax: Axes) -> None:
        super()._extract_info(ax)

        for line in ax.get_lines():
            if is_grid_line(line):
                continue
            label = line.get_label()
            if label.startswith("_child"):
                number = int(label[6:])
                label = f"Line {number}"

            points = [(x, y) for x, y in zip(line.get_xdata(), line.get_ydata())]
            line_data = PointData(label=label, points=points)
            self.elements.append(line_data)


class ScatterGraph(PointGraph):
    type: Literal[GraphType.SCATTER] = GraphType.SCATTER

    def _extract_info(self, ax: Axes) -> None:
        super()._extract_info(ax)

        for collection in ax.collections:
            points = [(x, y) for x, y in collection.get_offsets()]
            scatter_data = PointData(label=collection.get_label(), points=points)
            self.elements.append(scatter_data)
