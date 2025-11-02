from textual import on
from textual.app import App, ComposeResult

from textual_hires_canvas import Canvas, HiResMode, TextAlign


class MinimalApp(App[None]):
    def compose(self) -> ComposeResult:
        yield Canvas()

    @on(Canvas.Resize)
    def draw(self, event: Canvas.Resize):
        canvas = event.canvas
        size = event.size
        canvas.reset(size=event.size)

        canvas.draw_rectangle_box(0, 0, size.width - 1, size.height - 1, thickness=2)
        canvas.draw_line(1, 1, size.width - 2, size.height - 2, style="green")
        canvas.draw_hires_line(
            1, size.height - 1.5, size.width - 1.5, 1, HiResMode.BRAILLE, style="blue"
        )
        canvas.write_text(
            size.width // 2,
            1,
            "A [italic]simple[/] demo of the [bold yellow]Canvas[/]",
            TextAlign.CENTER,
        )


if __name__ == "__main__":
    MinimalApp().run()
