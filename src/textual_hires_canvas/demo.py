from math import floor

from textual import on
from textual.app import App, ComposeResult

from textual_hires_canvas.canvas import Canvas
from textual_hires_canvas.hires import HiResMode


class DemoApp(App[None]):
    _bx = 0
    _bdx = 1
    _by = 0
    _bdy = 1
    _tidx = 0.0

    def compose(self) -> ComposeResult:
        yield Canvas(40, 20)

    def on_mount(self) -> None:
        self.set_interval(1 / 10, self.redraw_canvas)

    @on(Canvas.Resize)
    def resize(self, event: Canvas.Resize) -> None:
        event.canvas.reset(size=event.size)

    def redraw_canvas(self) -> None:
        canvas = self.query_one(Canvas)
        canvas.reset()
        canvas.draw_hires_line(2, 10, 78, 2, hires_mode=HiResMode.BRAILLE, style="blue")
        canvas.draw_hires_line(2, 5, 78, 10, hires_mode=HiResMode.BRAILLE)
        canvas.draw_line(0, 0, 8, 8)
        canvas.draw_line(0, 19, 39, 0, char="X", style="red")
        canvas.write_text(
            floor(self._tidx),
            10,
            "[green]This text is [bold]easy[/bold] to read",
        )
        canvas.draw_rectangle_box(
            self._bx, self._by, self._bx + 20, self._by + 10, thickness=2
        )
        self._bx += self._bdx
        if (self._bx <= 0) or (self._bx + 20 >= canvas.size.width - 1):
            self._bdx *= -1
        self._by += self._bdy
        if (self._by <= 0) or (self._by + 10 >= canvas.size.height - 1):
            self._bdy *= -1
        self._tidx += 0.5
        if self._tidx >= canvas.size.width + 20:
            self._tidx = -20


if __name__ == "__main__":
    DemoApp().run()
