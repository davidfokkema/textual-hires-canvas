from __future__ import annotations
from textual import on, events
from textual.app import App, ComposeResult
from textual.containers import Container
from textual_hires_canvas import Canvas


class CustomCanvas(Canvas):

    @on(Canvas.Resize)
    def handle_canvas_resize(self, event: Canvas.Resize) -> None:
        self.reset(size=event.size, refresh=True)

    def clear_canvas(self) -> None:
        """Clear the canvas."""

        assert self._canvas_size, "Invalid canvas size."
        width = self._canvas_size.width
        height = self._canvas_size.height
        self._buffer = [[" "] * width for _ in range(height)]
        self._styles = [[""] * width for _ in range(height)]
        self.refresh()

    def on_mouse_down(self, event: events.MouseDown) -> None:

        if event.button == 1:  # left button
            self.position_on_down = event.offset
            self.capture_mouse()

    def on_mouse_up(self) -> None:
        self.release_mouse()
        self.clear_canvas()

    def on_mouse_move(self, event: events.MouseMove) -> None:

        if self.app.mouse_captured == self:
            self.clear_canvas()

            # Get the absolute position of the mouse right now (event.screen_offset),
            # minus where it was when the mouse was pressed down (position_on_down).
            total_delta = event.offset - self.position_on_down

            self.draw_rectangle_box(
                x0=self.position_on_down.x,
                y0=self.position_on_down.y,
                x1=self.position_on_down.x + total_delta.x,
                y1=self.position_on_down.y + total_delta.y,
                style="bold cyan",
            )

class MouseRectangleDragApp(App[None]):

    def compose(self) -> ComposeResult:
        yield CustomCanvas(id="canvas")

    def on_mount(self) -> None:
        canvas = self.query_one(CustomCanvas)
        canvas.reset(size=canvas.size, refresh=True)
        canvas.clear_canvas()


if __name__ == "__main__":
    MouseRectangleDragApp().run()
