import asyncio

from textual.app import App, ComposeResult

from textual_hires_canvas import Canvas, HiResMode


class CanvasApp(App[None]):
    def compose(self) -> ComposeResult:
        yield Canvas(10, 5)


def draw(*shapes: tuple[float, float, float, float, str]) -> Canvas:
    """Draw half-block rectangles on a 10x5 canvas and return it."""

    async def run() -> Canvas:
        app = CanvasApp()
        async with app.run_test():
            canvas = app.query_one(Canvas)
            for x0, y0, x1, y1, style in shapes:
                canvas.draw_filled_hires_rectangle(
                    x0, y0, x1, y1, hires_mode=HiResMode.HALFBLOCK, style=style
                )
            return canvas

    return asyncio.run(run())


def test_lower_half_keeps_upper_colour() -> None:
    # green fills rows 0-3, then red covers rows 2.5-4: cell row 2 is half/half
    canvas = draw((0, 0, 3, 4, "green"), (0, 2.5, 3, 4, "red"))
    assert canvas.get_pixel(1, 1) == ("█", "green")
    assert canvas.get_pixel(1, 2) == ("▀", "green on red")
    assert canvas.get_pixel(1, 3) == ("█", "red")


def test_upper_half_keeps_lower_colour() -> None:
    canvas = draw((0, 0, 3, 4, "green"), (0, 0, 3, 1.5, "red"))
    assert canvas.get_pixel(1, 1) == ("▀", "red on green")


def test_both_halves_same_colour_become_full_block() -> None:
    canvas = draw((0, 0, 3, 1.5, "red"), (0, 1.5, 3, 3, "red"))
    assert canvas.get_pixel(1, 1) == ("█", "red")


def test_half_block_on_empty_cell_is_unchanged() -> None:
    canvas = draw((0, 0, 3, 1.5, "red"))
    assert canvas.get_pixel(1, 1) == ("▀", "red")
    assert canvas.get_pixel(1, 2) == (" ", "")


def test_other_characters_are_replaced() -> None:
    async def run() -> Canvas:
        app = CanvasApp()
        async with app.run_test():
            canvas = app.query_one(Canvas)
            canvas.set_pixel(1, 1, "x", "blue")
            canvas.draw_filled_hires_rectangle(
                0, 0, 3, 1.5, hires_mode=HiResMode.HALFBLOCK, style="red"
            )
            return canvas

    assert asyncio.run(run()).get_pixel(1, 1) == ("▀", "red")
