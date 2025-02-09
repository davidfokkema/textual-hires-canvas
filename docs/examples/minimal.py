from textual.app import App, ComposeResult

from textual_hires_canvas import Canvas, HiResMode, TextAlign


class MinimalApp(App[None]):
    def compose(self) -> ComposeResult:
        yield Canvas(40, 20)

    def on_mount(self) -> None:
        canvas = self.query_one(Canvas)
        canvas.draw_rectangle_box(0, 0, 39, 19, thickness=2)
        canvas.draw_line(1, 1, 38, 18, style="green")
        canvas.draw_hires_line(1, 18.5, 38.5, 1, HiResMode.BRAILLE, style="blue")
        canvas.write_text(
            20,
            1,
            "A [italic]simple[/] demo of the [bold yellow]Canvas[/]",
            TextAlign.CENTER,
        )


if __name__ == "__main__":
    MinimalApp().run()
