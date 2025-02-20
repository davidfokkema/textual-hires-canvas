import enum
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from math import floor

import numpy as np
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual._box_drawing import BOX_CHARACTERS
from textual.geometry import Region, Size
from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget

from textual_hires_canvas.hires import HiResMode, hires_sizes, pixels

get_box = BOX_CHARACTERS.__getitem__


class TextAlign(enum.Enum):
    LEFT = enum.auto()
    CENTER = enum.auto()
    RIGHT = enum.auto()


class Canvas(Widget):
    """A widget that renders a 2D canvas."""

    @dataclass
    class Resize(Message):
        canvas: "Canvas"
        size: Size

    _canvas_size: Size | None = None
    _canvas_region: Region | None = None
    _buffer: list[list[str]]
    _styles: list[list[str]]

    # FIXME: move this to PlotWidget, it has no place here.
    scale_rectangle: Region | None = None

    def __init__(
        self,
        width: int | None = None,
        height: int | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        # FIXME: move this to PlotWidget, it has no place here.
        scale_rectangle: Region | None = None,
        disabled: bool = False,
    ):
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)

        self._buffer = []
        self._styles = []
        self.scale_rectangle = scale_rectangle

        if width is not None and height is not None:
            self.reset(size=Size(width, height), refresh=False)

    def _on_resize(self, event: Resize) -> None:
        self.post_message(self.Resize(canvas=self, size=event.size))

    def reset(self, size: Size | None = None, refresh: bool = True) -> None:
        """Resets the canvas to the specified size or to the current size if no size is provided.
        Clears buffers,styles and dirty cache, and resets the canvas size.

        Args:
            size: The new size for the canvas.
            refresh: Whether to refresh the canvas after resetting.
        Returns:
            self for chaining.
        """
        if size:
            self._canvas_size = size
            self._canvas_region = Region(0, 0, size.width, size.height)
            self.scale_rectangle = Region(1, 1, size.width - 2, size.height - 2)

        if self._canvas_size:
            self._buffer = [
                [" " for _ in range(self._canvas_size.width)]
                for _ in range(self._canvas_size.height)
            ]
            self._styles = [
                ["" for _ in range(self._canvas_size.width)]
                for _ in range(self._canvas_size.height)
            ]

        if refresh:
            self.refresh()

    def render_line(self, y: int) -> Strip:
        """Renders a single line of the canvas at the given y-coordinate.

        Args:
            y: The y-coordinate of the line.
        Returns:
            A Strip representing the line.
        """
        if self._canvas_size is None:
            return Strip([Segment("")])
        if y < self._canvas_size.height:
            return Strip(
                [
                    Segment(char, style=Style.parse(style))
                    for char, style in zip(self._buffer[y], self._styles[y])
                ]
            ).simplify()
        return Strip([])

    def set_pixel(self, x: int, y: int, char: str = "█", style: str = "white") -> None:
        """Sets a single pixel at the given coordinates.
        Also marks it dirty for refreshing.

        Args:
            x: The x-coordinate of the pixel.
            y: The y-coordinate of the pixel.
            char: The character to draw.
            style: The style to apply to the character.
        """
        assert self._canvas_region is not None
        if not self._canvas_region.contains(x, y):
            # coordinates are outside canvas
            return

        self._buffer[y][x] = char
        self._styles[y][x] = style
        self.refresh()

    def set_pixels(
        self,
        coordinates: Iterable[tuple[int, int]],
        char: str = "█",
        style: str = "white",
    ) -> None:
        """Sets multiple pixels at the given coordinates.

        Args:
            coordinates: An iterable of tuples representing the coordinates of the pixels.
            char: The character to draw.
            style: The style to apply to the character.
        """
        for x, y in coordinates:
            self.set_pixel(x, y, char, style)

    def set_hires_pixels(
        self,
        coordinates: Iterable[tuple[float, float]],
        hires_mode: HiResMode = HiResMode.HALFBLOCK,
        style: str = "white",
    ) -> None:
        """Sets multiple pixels at the given coordinates using the specified Hi-Res mode.

        Args:
            coordinates: An iterable of tuples representing the coordinates of the pixels.
            hires_mode: The Hi-Res mode to use.
            style: The style to apply to the character.
        """
        assert self._canvas_size is not None
        assert self._canvas_region is not None
        pixel_size = hires_sizes[hires_mode]
        hires_size_x = self._canvas_size.width * pixel_size.width
        hires_size_y = self._canvas_size.height * pixel_size.height
        hires_buffer = np.zeros(
            shape=(hires_size_y, hires_size_x),
            dtype=bool,
        )
        pixel_info = pixels.get(hires_mode)
        assert pixel_info is not None
        for x, y in coordinates:
            if not self._canvas_region.contains(floor(x), floor(y)):
                # coordinates are outside canvas
                continue
            hires_buffer[floor(y * pixel_size.height)][floor(x * pixel_size.width)] = (
                True
            )
        for x in range(0, hires_size_x, pixel_size.width):
            for y in range(0, hires_size_y, pixel_size.height):
                subarray = hires_buffer[
                    y : y + pixel_size.height, x : x + pixel_size.width
                ]
                subpixels = tuple(int(v) for v in subarray.flat)
                if char := pixel_info[subpixels]:
                    self.set_pixel(
                        x // pixel_size.width,
                        y // pixel_size.height,
                        char=char,
                        style=style,
                    )

    def get_pixel(self, x: int, y: int) -> tuple[str, str]:
        """Retrieves the character and style of a single pixel at the given coordinates.

        Args:
            x: The x-coordinate of the pixel.
            y: The y-coordinate of the pixel.
        Returns:
            A tuple containing the character and style of the pixel.
        """
        return self._buffer[y][x], self._styles[y][x]

    def draw_line(
        self, x0: int, y0: int, x1: int, y1: int, char: str = "█", style: str = "white"
    ) -> None:
        """Draws a line from (x0, y0) to (x1, y1) using the specified character and style.

        Args:
            x0: The x-coordinate of the start of the line.
            y0: The y-coordinate of the start of the line.
            x1: The x-coordinate of the end of the line.
            y1: The y-coordinate of the end of the line.
            char: The character to draw.
            style: The style to apply to the character.
        """
        assert self._canvas_region is not None
        if not self._canvas_region.contains(
            x0, y0
        ) and not self._canvas_region.contains(x1, y1):
            return
        self.set_pixels(self._get_line_coordinates(x0, y0, x1, y1), char, style)

    def draw_lines(
        self,
        coordinates: Iterable[tuple[int, int, int, int]],
        char: str = "█",
        style: str = "white",
    ) -> None:
        """Draws multiple lines from given coordinates using the specified character and style.

        Args:
            coordinates: An iterable of tuples representing the coordinates of the lines.
            char: The character to draw.
            style: The style to apply to the character.
        """
        for x0, y0, x1, y1 in coordinates:
            self.draw_line(x0, y0, x1, y1, char, style)

    def draw_hires_line(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        hires_mode: HiResMode = HiResMode.HALFBLOCK,
        style: str = "white",
    ) -> None:
        """Draws a high-resolution line from (x0, y0) to (x1, y1) using the specified character and style.

        Args:
            x0: The x-coordinate of the start of the line.
            y0: The y-coordinate of the start of the line.
            x1: The x-coordinate of the end of the line.
            y1: The y-coordinate of the end of the line.
            hires_mode: The high-resolution mode to use.
            style: The style to apply to the character.
        """
        self.draw_hires_lines([(x0, y0, x1, y1)], hires_mode, style)

    def draw_hires_lines(
        self,
        coordinates: Iterable[tuple[float, float, float, float]],
        hires_mode: HiResMode = HiResMode.HALFBLOCK,
        style: str = "white",
    ) -> None:
        """Draws multiple high-resolution lines from given coordinates using the specified character and style.

        Args:
            coordinates: An iterable of tuples representing the coordinates of the lines.
            hires_mode: The high-resolution mode to use.
            style: The style to apply to the character.
        """
        assert self._canvas_region is not None
        pixel_size = hires_sizes[hires_mode]
        pixels = []
        for x0, y0, x1, y1 in coordinates:
            if not self._canvas_region.contains(
                floor(x0), floor(y0)
            ) and not self._canvas_region.contains(floor(x1), floor(y1)):
                # coordinates are outside canvas
                continue
            coords = self._get_line_coordinates(
                floor(x0 * pixel_size.width),
                floor(y0 * pixel_size.height),
                floor(x1 * pixel_size.width),
                floor(y1 * pixel_size.height),
            )
            pixels.extend(
                [
                    (
                        x / pixel_size.width,
                        y / pixel_size.height,
                    )
                    for x, y in coords
                ]
            )
        self.set_hires_pixels(pixels, hires_mode, style)

    def draw_rectangle_box(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        thickness: int = 1,
        style: str = "white",
    ) -> None:
        """Draw a rectangle box with the specified thickness and style.

        Args:
            x0: The x-coordinate of the top-left corner.
            y0: The y-coordinate of the top-left corner.
            x1: The x-coordinate of the bottom-right corner.
            y1: The y-coordinate of the bottom-right corner.
            thickness: The thickness of the box.
            style: The style to apply to the characters.
        """
        T = thickness
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        self.set_pixel(x0, y0, char=get_box((0, T, T, 0)), style=style)
        self.set_pixel(x1, y0, char=get_box((0, 0, T, T)), style=style)
        self.set_pixel(x1, y1, char=get_box((T, 0, 0, T)), style=style)
        self.set_pixel(x0, y1, char=get_box((T, T, 0, 0)), style=style)
        for y in y0, y1:
            self.draw_line(
                x0 + 1, y, x1 - 1, y, char=get_box((0, T, 0, T)), style=style
            )
        for x in x0, x1:
            self.draw_line(
                x, y0 + 1, x, y1 - 1, char=get_box((T, 0, T, 0)), style=style
            )

    def write_text(
        self,
        x: int,
        y: int,
        text: str,
        align: TextAlign = TextAlign.LEFT,
    ) -> None:
        """Write text to the canvas at the specified position, with support for markup.

        Args:
            x (int): X-coordinate of the left edge of the text.
            y (int): Y-coordinate of the baseline of the text.
            text (str): Text to be written.
            align (TextAlign): The alignment of the text within the canvas.
        """
        if text == "":
            return

        assert self._canvas_size is not None
        if y < 0 or y >= self._canvas_size.height:
            return

        # parse markup
        rich_text = Text.from_markup(text)
        # store plain text
        plain_text = rich_text.plain
        # store styles for each individual character
        rich_styles = []
        for c in rich_text.divide(range(1, len(plain_text))):
            style = Style()
            for span in c._spans:
                style += Style.parse(span.style)
            rich_styles.append(style)

        if align == TextAlign.RIGHT:
            x -= len(plain_text) - 1
        elif align == TextAlign.CENTER:
            div, mod = divmod(len(plain_text), 2)
            x -= div
            if mod == 0:
                # even number of characters, shift one to the right since I just
                # like that better -- DF
                x += 1

        if x <= -len(plain_text) or x >= self._canvas_size.width:
            # no part of text falls inside the canvas
            return

        overflow_left = -x
        overflow_right = x + len(plain_text) - self._canvas_size.width
        if overflow_left > 0:
            buffer_left = 0
            text_left = overflow_left
        else:
            buffer_left = x
            text_left = 0
        if overflow_right > 0:
            buffer_right = None
            text_right = -overflow_right
        else:
            buffer_right = x + len(plain_text)
            text_right = None

        self._buffer[y][buffer_left:buffer_right] = plain_text[text_left:text_right]
        self._styles[y][buffer_left:buffer_right] = [
            str(s) for s in rich_styles[text_left:text_right]
        ]
        assert len(self._buffer[y]) == self._canvas_size.width
        assert len(self._styles[y]) == self._canvas_size.width
        self.refresh()

    def _get_line_coordinates(
        self, x0: int, y0: int, x1: int, y1: int
    ) -> Iterator[tuple[int, int]]:
        """Get all pixel coordinates on the line between two points.

        Algorithm was taken from
        https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm and
        translated to Python.

        Args:
            x0: starting point x coordinate
            y0: starting point y coordinate
            x1: end point x coordinate
            y1: end point y coordinate

        Yields:
            Tuples of (x, y) coordinates that make up the line.
        """
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        error = dx + dy

        while True:
            yield x0, y0
            e2 = 2 * error
            if e2 >= dy:
                if x0 == x1:
                    break
                error = error + dy
                x0 = x0 + sx
            if e2 <= dx:
                if y0 == y1:
                    break
                error = error + dx
                y0 = y0 + sy
