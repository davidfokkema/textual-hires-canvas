import asyncio
import random
import time

from rich.color import ANSI_COLOR_NAMES
from textual import work
from textual.app import App, ComposeResult

from textual_hires_canvas import Canvas, HiResMode

N = 10_000

X = -100, 100
Y = -100, 100
# X = 0, 79
# Y = 0, 24


class MinimalApp(App[None]):
    t = 0

    def compose(self) -> ComposeResult:
        yield Canvas(80, 24)

    def on_mount(self) -> None:
        self.draw()

    @work
    async def draw(self) -> None:
        canvas = self.query_one(Canvas)
        for _ in range(N):
            x0 = round(random.uniform(*X))
            y0 = round(random.uniform(*Y))
            x1 = round(random.uniform(*X))
            y1 = round(random.uniform(*Y))
            style = random.choice(list(ANSI_COLOR_NAMES.keys()))

            x0, x1 = sorted([x0, x1])
            y0, y1 = sorted([y0, y1])

            t0 = time.monotonic_ns()
            # canvas.draw_rectangle_box(x0, y0, x1, y1, thickness=2, style=style)
            # canvas.draw_filled_quad(x0, y0, x0, y1, x1, y1, x1, y0, style=style)
            canvas.draw_filled_rectangle(x0, y0, x1, y1, style=style)
            self.t += time.monotonic_ns() - t0
            await asyncio.sleep(0)
        await self.action_quit()


if __name__ == "__main__":
    (app := MinimalApp()).run()
    print(f"Total time for {N} rectangles: {app.t / 1e9:.3f} s.")
