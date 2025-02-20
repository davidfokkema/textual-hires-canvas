from math import floor

from textual import on
from textual.app import App, ComposeResult

from textual_hires_canvas import Canvas, HiResMode


class DemoApp(App[None]):
    _box_x_pos = 0
    _box_y_pos = 0
    _text_x_pos = 0.0

    _box_x_step = 1
    _box_y_step = 1
    _text_x_step = 0.5

    def compose(self) -> ComposeResult:
        yield Canvas(1, 1)

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
            floor(self._text_x_pos),
            10,
            "[green]This text is [bold]easy[/bold] to read",
        )
        canvas.draw_rectangle_box(
            self._box_x_pos,
            self._box_y_pos,
            self._box_x_pos + 20,
            self._box_y_pos + 10,
            thickness=2,
        )
        self._box_x_pos += self._box_x_step
        if (self._box_x_pos <= 0) or (self._box_x_pos + 20 >= canvas.size.width - 1):
            self._box_x_step *= -1
        self._box_y_pos += self._box_y_step
        if (self._box_y_pos <= 0) or (self._box_y_pos + 10 >= canvas.size.height - 1):
            self._box_y_step *= -1
        self._text_x_pos += self._text_x_step
        if self._text_x_pos >= canvas.size.width + 20:
            self._text_x_pos = -20


def main():
    DemoApp().run()


if __name__ == "__main__":
    main()
