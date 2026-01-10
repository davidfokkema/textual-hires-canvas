import asyncio
import random
import time

from rich.color import ANSI_COLOR_NAMES
from textual import work
from textual.app import App, ComposeResult
from textual.events import Key
from textual.widgets import Label

from textual_hires_canvas import Canvas, HiResMode

N = 100

# X = -100, 100
# Y = -100, 100
X = 0, 79
Y = 0, 24


class MinimalApp(App[None]):
    t = 0
    xshift = 0
    yshift = 0

    def compose(self) -> ComposeResult:
        yield Label("xshift: 0.0", id="xshift")
        yield Label("yshift: 0.0", id="yshift")
        yield Canvas(80, 24)

    def on_mount(self) -> None:
        self.draw_single_rectangle()

    def draw_single_rectangle(self) -> None:
        canvas = self.query_one(Canvas)
        canvas.reset()
        canvas.draw_filled_hires_rectangle(
            10 + self.xshift,
            3 + self.yshift,
            60 + self.xshift,
            18 + self.yshift,
            hires_mode=HiResMode.HALFBLOCK,
        )

    def on_key(self, event: Key) -> None:
        if event.key == "left":
            self.xshift -= 0.1
        elif event.key == "right":
            self.xshift += 0.1
        elif event.key == "up":
            self.yshift -= 0.1
        elif event.key == "down":
            self.yshift += 0.1
        self.query_one("#xshift", Label).update(f"xshift: {self.xshift:.1f}")
        self.query_one("#yshift", Label).update(f"yshift: {self.yshift:.1f}")
        self.draw_single_rectangle()

    @work
    async def draw(self) -> None:
        canvas = self.query_one(Canvas)
        for _ in range(N):
            # x0 = round(random.uniform(*X))
            # y0 = round(random.uniform(*Y))
            # x1 = round(random.uniform(*X))
            # y1 = round(random.uniform(*Y))
            x0 = random.uniform(*X)
            y0 = random.uniform(*Y)
            x1 = random.uniform(*X)
            y1 = random.uniform(*Y)

            style = random.choice(list(ANSI_COLOR_NAMES.keys()))

            x0, x1 = sorted([x0, x1])
            y0, y1 = sorted([y0, y1])

            t0 = time.monotonic_ns()
            # canvas.draw_filled_quad(x0, y0, x0, y1, x1, y1, x1, y0, style=style)
            # canvas.draw_filled_rectangle(x0, y0, x1, y1, style=style)
            # canvas.draw_rectangle_box(
            #     round(x0), round(y0), round(x1), round(y1), thickness=2, style=style
            # )
            canvas.draw_filled_hires_rectangle(
                x0, y0, x1, y1, style=style, hires_mode=HiResMode.BRAILLE
            )
            # canvas.draw_hires_line(x0, y0, x1, y1, style=style)
            self.t += time.monotonic_ns() - t0
            await asyncio.sleep(0.05)
        # await self.action_quit()


if __name__ == "__main__":
    (app := MinimalApp()).run()
    print(f"Total time for {N} rectangles: {app.t / 1e9:.3f} s.")
