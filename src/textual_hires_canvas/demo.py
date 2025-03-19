import time
from math import floor

from textual import on
from textual.app import App, ComposeResult

from textual_hires_canvas import Canvas, HiResMode


class DemoApp(App[None]):
    _bx = 0.0
    _bdx = 0.1
    _by = 0.0
    _bdy = 0.1
    _tidx = 0.0
    _frame_count = 0
    _fps: float = 0.0
    _last_time = 0.0
    _canvas = Canvas(80, 20)
    _fps_history: list[float] = []
    _graph_width = 40
    _graph_height = 15
    _graph_lines: list[tuple[float, float, float, float]] = []

    def compose(self) -> ComposeResult:
        yield self._canvas

    def on_mount(self) -> None:
        self.set_interval(1 / 60, self.redraw_canvas)
        self.set_interval(1, self.calc_fps)
        self._fps_history = [0.0] * self._graph_width
        self._last_time = time.time()
        self.calc_fps()

    @on(Canvas.Resize)
    def resize(self, event: Canvas.Resize) -> None:
        event.canvas.reset(size=event.size)

    def build_fps_graph_line(
        self, i: int, v: float
    ) -> tuple[float, float, float, float]:
        return (
            i + 1,
            self._canvas.size.height - 1,
            i + 1,
            self._canvas.size.height - (v / 60.0 * self._graph_height + 1),
        )

    def calc_fps(self) -> None:
        """Calculate the FPS and update the graph lines."""
        curr_time = time.time()
        delta = curr_time - self._last_time

        if delta > 0:
            self._fps = self._frame_count / delta
        else:
            self._fps = 0

        self._frame_count = 0
        self._fps_history.append(self._fps)
        self._fps_history.pop(0)
        self._graph_lines = [
            self.build_fps_graph_line(i, fps) for i, fps in enumerate(self._fps_history)
        ]
        self._last_time = time.time()

    def draw_fps_charts(self) -> None:
        """Draw the FPS charts on the canvas."""
        canvas = self._canvas

        canvas.draw_rectangle_box(
            0,
            canvas.size.height - 1,
            len(self._fps_history) + 1,
            canvas.size.height - self._graph_height - 3,
            thickness=2,
        )
        canvas.write_text(
            int(len(self._fps_history) / 2) - 4,
            canvas.size.height - self._graph_height - 3,
            f"[bold]FPS: {self._fps:.1f}[/bold]",
        )

        canvas.draw_hires_lines(
            self._graph_lines,
            style="red",
            hires_mode=HiResMode.HALFBLOCK,
        )

    def redraw_canvas(self) -> None:
        self._frame_count += 1
        canvas = self._canvas
        with canvas.batch_refresh():
            canvas.reset()
            canvas.draw_hires_line(
                0,
                0,
                canvas.size.width / 2,
                canvas.size.height / 2,
                hires_mode=HiResMode.BRAILLE,
                style="blue",
            )
            canvas.draw_hires_line(2, 5, 78, 10, hires_mode=HiResMode.BRAILLE)
            canvas.draw_line(0, 0, 8, 8)
            canvas.draw_line(0, 19, 39, 0, char="X", style="red")
            canvas.write_text(
                floor(self._tidx),
                10,
                "[green]This text is [bold]easy[/bold] to read",
            )
            canvas.draw_rectangle_box(
                int(self._bx),
                int(self._by),
                int(self._bx + 20),
                int(self._by + 10),
                thickness=2,
            )
            self._bx += self._bdx
            if (self._bx <= 0) or (self._bx + 20 >= canvas.size.width - 1):
                self._bdx *= -1
            self._by += self._bdy
            if (self._by <= 0) or (self._by + 10 >= canvas.size.height - 1):
                self._bdy *= -1
            self._tidx += 0.1
            if self._tidx >= canvas.size.width + 20:
                self._tidx = -20

            self.draw_fps_charts()


def main() -> None:
    DemoApp().run()


if __name__ == "__main__":
    main()
