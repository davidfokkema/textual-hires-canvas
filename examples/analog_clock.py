from __future__ import annotations

import math
from datetime import datetime
from typing import NamedTuple

from textual.app import App, ComposeResult
from textual_hires_canvas import Canvas, HiResMode
from textual.reactive import var


class Point(NamedTuple):
    x: float
    y: float

    def __add__(self, other: Point | tuple) -> Point:
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y)
        elif isinstance(other, tuple):
            return Point(self.x + other[0], self.y + other[1])
        return NotImplemented


class AnalogClockApp(App[None]):
    """Textual application with an analog clock."""

    time = var[datetime](datetime.now)
    """Current time set by the `tick` timer."""

    def _on_mount(self) -> None:
        self.tick = self.set_interval(1, lambda: setattr(self, "time", datetime.now()))

    def _watch_time(self, time: datetime) -> None:
        self.draw_time(time)

    def compose(self) -> ComposeResult:
        yield Canvas(*self.size)

    def draw_time(self, time: datetime) -> None:
        """Draw the current time and clock frame.

        Args:
            time: The time to draw.
        """
        canvas = self.query_one(Canvas)
        canvas.reset(self.size, refresh=False)

        origin = Point(canvas.size.width // 2, canvas.size.height // 2)
        radius = canvas.size.height * 0.8
        self._draw_arms(canvas, radius, time, origin)
        self._draw_clock(canvas, origin, radius)

    def _draw_arms(
        self,
        canvas: Canvas,
        radius: int,
        time: datetime,
        origin: Point,
    ) -> None:
        sx, sy = self._calculate_second_arm(time.second, radius, origin)
        canvas.draw_hires_line(*origin, sx, sy)

        minute = time.minute + (time.second / 60)
        mx, my = self._calculate_min_arm(minute, radius, origin)
        canvas.draw_hires_line(*origin, mx, my, style="yellow")

        hour = time.hour + (minute / 60)
        hx, hy = self._calculate_hours_arm(hour, radius, origin)
        canvas.draw_hires_line(*origin, hx, hy, style="red")

    def _draw_clock(self, canvas: Canvas, origin: Point, radius: float) -> None:
        canvas.draw_hires_circle(*origin, radius, hires_mode=HiResMode.QUADRANT)
        radius *= 0.5
        start = radius * 0.8
        end = radius * 0.9

        lines = list[tuple[float, float, float, float]]()
        for angle in range(0, 360, 30):
            radian = math.radians(angle)
            start_pt = self._calculate_position(radian, start, origin)
            stop_pt = self._calculate_position(radian, end, origin)
            lines.append((*start_pt, *stop_pt))

        canvas.draw_hires_lines(lines)

    def _calculate_hours_arm(self, hours: float, radius: float, origin: Point) -> Point:
        radius *= 0.34
        total = math.radians((hours * 30) - 90)
        return self._calculate_position(total, radius, origin)

    def _calculate_min_arm(self, minutes: float, radius: float, origin: Point) -> Point:
        radius *= 0.4
        total = math.radians((minutes * 6) - 90)
        return self._calculate_position(total, radius, origin)

    def _calculate_second_arm(
        self, seconds: float, radius: float, origin: Point
    ) -> Point:
        radius *= 0.45
        radian = math.radians((seconds * 6) - 90)
        return self._calculate_position(radian, radius, origin)

    def _calculate_position(
        self,
        radian: float,
        radius: float,
        origin: Point,
    ) -> Point:
        x = math.cos(radian)
        y = math.sin(radian)

        return Point((x * (radius * 2)), (y * radius)) + origin


if __name__ == "__main__":
    AnalogClockApp().run()
