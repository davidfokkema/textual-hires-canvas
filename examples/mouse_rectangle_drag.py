from __future__ import annotations

from textual import events, on
from textual.app import App, ComposeResult
from textual.widgets import Label

from textual_hires_canvas import Canvas


class MouseDragCanvas(Canvas):
    @on(Canvas.Resize)
    def handle_canvas_resize(self, event: Canvas.Resize) -> None:
        self.reset(size=event.size, refresh=True)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button == 1:  # left button
            self.position_on_down = event.offset
            self.capture_mouse()

    def on_mouse_up(self) -> None:
        self.release_mouse()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self.app.mouse_captured == self:
            self.reset()

            # Get the absolute position of the mouse right now (event.offset),
            # minus where it was when the mouse was pressed down.
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
        yield Label("Click and drag rectangles with your mouse.")
        yield MouseDragCanvas()


if __name__ == "__main__":
    MouseRectangleDragApp().run()
