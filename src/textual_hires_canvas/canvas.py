import enum
import sys
from collections.abc import AsyncIterator, Iterable, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from math import floor

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from typing import Callable, TypeAlias

import numpy as np
from numpy.typing import NDArray
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual._box_drawing import BOX_CHARACTERS
from textual.geometry import Region, Size
from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget

from textual_hires_canvas.hires import HiResMode, hires_sizes, pixels

FloatScalar: TypeAlias = float | np.floating
FloatArray: TypeAlias = NDArray[np.floating]

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

    default_hires_mode: HiResMode

    _canvas_size: Size
    _canvas_region: Region
    _buffer: list[list[str]]
    _styles: list[list[str]]

    # Style cache to avoid reparsing identical style strings
    _style_cache: dict[str, Style] = {}

    def __init__(
        self,
        width: int = 40,
        height: int = 20,
        default_hires_mode: HiResMode | None = HiResMode.BRAILLE,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        """Initialize the Canvas widget.

        Args:
            width: The width of the canvas. Defaults to 40.
            height: The height of the canvas. Defaults to 20.
            default_hires_mode: The default high-resolution mode. Defaults to
                HiresMode.BRAILLE.
            name: The name of the widget. Defaults to None.
            id: The ID of the widget. Defaults to None.
            classes: The CSS classes of the widget. Defaults to None.
            disabled: Whether the widget is disabled. Defaults to False.
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)

        self._refreshes_pending: int = 0
        # reference count batch refreshes

        self._buffer = []
        self._styles = []
        self._canvas_size = Size(0, 0)
        self._canvas_region = Region()

        self.default_hires_mode = default_hires_mode or HiResMode.BRAILLE

        self.reset(size=Size(width, height), refresh=False)

    @contextmanager
    def batch_refresh(self) -> Iterator[None]:
        """Context manager that defers call to refresh until exiting the context.

        This is useful when making multiple changes to the canvas and only wanting
        to trigger refresh once at the end.

        Example:
            ```python
            with canvas.batch_changes():
                canvas.set_pixel(0, 0)
                canvas.set_pixel(1, 1)
                canvas.set_pixel(2, 2)
            # Refresh called
            ```

        Yields:
            Iterator[None]: A context manager.
        """
        self._refreshes_pending += 1
        try:
            yield
        finally:
            self._refreshes_pending -= 1
            if self._refreshes_pending == 0:
                self.refresh()

    @asynccontextmanager
    async def async_batch_refresh(self) -> AsyncIterator[None]:
        """Async context manager that defers call to refresh until exiting the context.

        This is useful when making multiple asynchronous changes to the canvas and only wanting
        to trigger refresh once at the end.

        Example:
                Yields:
        AsyncIterator[None]: An async context manager.
        """
        self._refreshes_pending += 1
        try:
            yield
        finally:
            self._refreshes_pending -= 1
            if self._refreshes_pending == 0:
                self.refresh()

    def refresh(
        self,
        *regions: Region,
        repaint: bool = True,
        layout: bool = False,
        recompose: bool = False,
    ) -> Self:
        if self._refreshes_pending:
            return self
        super().refresh(*regions, repaint=repaint, layout=layout, recompose=recompose)
        return self

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
        # Update size and regions if provided
        if size:
            self._canvas_size = size
            self._canvas_region = Region(0, 0, size.width, size.height)

        # Initialize buffers if we have a valid size
        if self._canvas_size:
            width = self._canvas_size.width
            height = self._canvas_size.height

            # More efficient buffer creation using list comprehension with multiplication
            # This is significantly faster than nested loops for large buffers
            self._buffer = [[" "] * width for _ in range(height)]
            self._styles = [[""] * width for _ in range(height)]

        # Only refresh if requested
        if refresh:
            self.refresh()

    def render_line(self, y: int) -> Strip:
        """Renders a single line of the canvas at the given y-coordinate.

        Args:
            y: The y-coordinate of the line.
        Returns:
            A Strip representing the line.
        """
        # Fast path for out-of-bounds or uninitialized
        if not self._canvas_size.area or y >= self._canvas_size.height:
            return Strip.blank(cell_length=0)

        buffer_line = self._buffer[y]
        styles_line = self._styles[y]

        # Fast path for blank lines
        if all(char == " " for char in buffer_line):
            return Strip.blank(cell_length=len(buffer_line))

        # Create segments with batching by style
        segments: list[Segment] = []
        append = segments.append  # Local reference for faster calls

        # Batch processing for same style segments
        current_style_str = None
        current_style_obj = None
        current_text = ""

        for char, style_str in zip(buffer_line, styles_line):
            # When style changes, add current batch and start new one
            if style_str != current_style_str:
                # Add current batch if it exists
                if current_text:
                    append(Segment(current_text, style=current_style_obj))

                # Start new batch
                current_style_str = style_str
                current_text = char

                # Get style object from cache or create new one
                if style_str:
                    if style_str not in self._style_cache:
                        self._style_cache[style_str] = Style.parse(style_str)
                    current_style_obj = self._style_cache[style_str]
                else:
                    current_style_obj = None
            else:
                # Add to current batch
                current_text += char

        # Add the final batch
        if current_text:
            append(Segment(current_text, style=current_style_obj))

        return Strip(segments).simplify()

    def get_pixel(self, x: int, y: int) -> tuple[str, str]:
        """Retrieves the character and style of a single pixel at the given coordinates.

        Args:
            x: The x-coordinate of the pixel.
            y: The y-coordinate of the pixel.
        Returns:
            A tuple containing the character and style of the pixel.
        """
        return self._buffer[y][x], self._styles[y][x]

    def set_pixel(self, x: int, y: int, char: str = "█", style: str = "white") -> None:
        """Sets a single pixel at the given coordinates.
        Also marks it dirty for refreshing.

        Args:
            x: The x-coordinate of the pixel.
            y: The y-coordinate of the pixel.
            char: The character to draw.
            style: The style to apply to the character.
        """
        # Fast rejection path without assert for performance
        if not (
            0 <= x < self._canvas_region.width and 0 <= y < self._canvas_region.height
        ):
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
        # Check if we have coordinates
        coord_list = list(coordinates)
        if not coord_list:
            return

        # Batch updates to avoid calling refresh for each pixel
        # Cache properties for faster access in the loop
        buffer = self._buffer
        styles = self._styles
        width = self._canvas_region.width
        height = self._canvas_region.height

        # Process all pixels first, then refresh once
        for x, y in coord_list:
            if 0 <= x < width and 0 <= y < height:
                buffer[y][x] = char
                styles[y][x] = style

        # Only refresh once after all updates
        self.refresh()

    def set_hires_pixels(
        self,
        coordinates: Iterable[tuple[FloatScalar, FloatScalar]],
        hires_mode: HiResMode | None = None,
        style: str = "white",
    ) -> None:
        """Sets multiple pixels at the given coordinates using the specified Hi-Res mode.

        Args:
            coordinates: An iterable of tuples representing the coordinates of the pixels.
            hires_mode: The Hi-Res mode to use.
            style: The style to apply to the character.
        """
        # Use default mode if none provided
        hires_mode = hires_mode or self.default_hires_mode
        pixel_size = hires_sizes[hires_mode]
        pixel_info = pixels.get(hires_mode)
        assert pixel_info is not None

        # Group coordinates by their cell position to minimize buffer operations
        cells_to_update: dict[tuple[int, int], set[tuple[int, int]]] = {}

        # Pre-compute these values outside the loop for better performance
        w_factor = pixel_size.width
        h_factor = pixel_size.height

        # Process all coordinates and group them by their target cell
        for x, y in coordinates:
            # Early rejection for out-of-bounds
            if not self._canvas_region.contains(floor(x), floor(y)):
                continue

            # Calculate high-res coordinates
            hx = floor(x * w_factor)
            hy = floor(y * h_factor)

            # Calculate which cell this belongs to and offset within cell
            cell_x = hx // w_factor
            cell_y = hy // h_factor

            # Get or create the set for this cell
            cell_key = (cell_x, cell_y)
            if cell_key not in cells_to_update:
                cells_to_update[cell_key] = set()

            # Add this point to the cell's set
            offset_x = hx % w_factor
            offset_y = hy % h_factor
            cells_to_update[cell_key].add((offset_x, offset_y))

        # Process each cell that needs updating
        for (cell_x, cell_y), points in cells_to_update.items():
            # Create a small buffer just for this cell
            cell_buffer = np.zeros((pixel_size.height, pixel_size.width), dtype=bool)

            # Mark each point in the buffer
            for offset_x, offset_y in points:
                cell_buffer[offset_y, offset_x] = True

            # Convert to subpixels and look up the character
            subpixels = tuple(int(v) for v in cell_buffer.flat)
            if char := pixel_info[subpixels]:
                self.set_pixel(
                    cell_x,
                    cell_y,
                    char=char,
                    style=style,
                )

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
        # Convert to list for multiple passes
        coord_list = list(coordinates)
        if not coord_list:
            return

        # Collect all pixels from all lines before rendering
        all_pixels = []

        for x0, y0, x1, y1 in coord_list:
            # Skip if both endpoints are outside the canvas
            if not self._canvas_region.contains(
                x0, y0
            ) and not self._canvas_region.contains(x1, y1):
                continue

            # Get coordinates for this line and extend the pixel collection
            line_pixels = self._get_line_coordinates(x0, y0, x1, y1)
            all_pixels.extend(line_pixels)

        # Draw all pixels at once with a single refresh
        if all_pixels:
            self.set_pixels(all_pixels, char, style)

    def draw_hires_line(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        hires_mode: HiResMode | None = None,
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
        coordinates: Iterable[
            tuple[FloatScalar, FloatScalar, FloatScalar, FloatScalar]
        ],
        hires_mode: HiResMode | None = None,
        style: str = "white",
    ) -> None:
        """Draws multiple high-resolution lines from given coordinates using the specified character and style.

        Args:
            coordinates: An iterable of tuples representing the coordinates of the lines.
            hires_mode: The high-resolution mode to use.
            style: The style to apply to the character.
        """
        # Early out if no coordinates
        if not coordinates:
            return

        # Convert to list if not already for multiple passes
        coord_list = list(coordinates)

        hires_mode = hires_mode or self.default_hires_mode
        pixel_size = hires_sizes[hires_mode]

        # Pre-compute multiplication factors once
        w_factor = pixel_size.width
        h_factor = pixel_size.height
        inv_w_factor = 1.0 / w_factor
        inv_h_factor = 1.0 / h_factor

        # Initialize an empty list for collecting pixel coordinates
        pixels: list[tuple[float, float]] = []
        pixels_append = pixels.append  # Local reference for faster calls

        # Process each line
        for x0, y0, x1, y1 in coord_list:
            # Skip if both endpoints are outside canvas (optimization)
            if not self._canvas_region.contains(
                floor(x0), floor(y0)
            ) and not self._canvas_region.contains(floor(x1), floor(y1)):
                continue

            # Convert to high-res grid coordinates
            hx0 = floor(x0 * w_factor)
            hy0 = floor(y0 * h_factor)
            hx1 = floor(x1 * w_factor)
            hy1 = floor(y1 * h_factor)

            # Get line coordinates
            coords = self._get_line_coordinates(hx0, hy0, hx1, hy1)

            # Convert back to canvas space and add to pixel array
            # Use direct append and precalculated factors for better performance
            for x, y in coords:
                pixels_append((x * inv_w_factor, y * inv_h_factor))

        # Only make one call to set_hires_pixels with all points
        if pixels:
            self.set_hires_pixels(pixels, hires_mode, style)

    def draw_triangle(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        style: str = "white",
    ) -> None:
        """Draw a triangle outline using the specified style.

        Args:
            x0: The x-coordinate of the first vertex.
            y0: The y-coordinate of the first vertex.
            x1: The x-coordinate of the second vertex.
            y1: The y-coordinate of the second vertex.
            x2: The x-coordinate of the third vertex.
            y2: The y-coordinate of the third vertex.
            style: The style to apply to the characters.
        """

        # Draw the three sides of the triangle
        self.draw_lines(
            [(x0, y0, x1, y1), (x1, y1, x2, y2), (x2, y2, x0, y0)], "█", style
        )

    def draw_hires_triangle(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        hires_mode: HiResMode | None = None,
        style: str = "white",
    ) -> None:
        """Draw a high-resolution triangle outline using the specified style.

        Args:
            x0: The x-coordinate of the first vertex.
            y0: The y-coordinate of the first vertex.
            x1: The x-coordinate of the second vertex.
            y1: The y-coordinate of the second vertex.
            x2: The x-coordinate of the third vertex.
            y2: The y-coordinate of the third vertex.
            hires_mode: The high-resolution mode to use.
            style: The style to apply to the characters.
        """

        # Draw the three sides of the triangle with high-resolution
        self.draw_hires_lines(
            [(x0, y0, x1, y1), (x1, y1, x2, y2), (x2, y2, x0, y0)], hires_mode, style
        )

    def draw_filled_triangle(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        style: str = "white",
    ) -> None:
        """Draw a filled triangle using the specified style.
        Uses a scanline algorithm for efficient filling.

        Args:
            x0: The x-coordinate of the first vertex.
            y0: The y-coordinate of the first vertex.
            x1: The x-coordinate of the second vertex.
            y1: The y-coordinate of the second vertex.
            x2: The x-coordinate of the third vertex.
            y2: The y-coordinate of the third vertex.
            style: The style to apply to the characters.
        """
        # Sort vertices by y-coordinate (y0 <= y1 <= y2)
        if y0 > y1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        if y1 > y2:
            x1, y1, x2, y2 = x2, y2, x1, y1
        if y0 > y1:
            x0, y0, x1, y1 = x1, y1, x0, y0

        # Skip if all points are the same or triangle has no height
        if (y0 == y1 == y2) or (y0 == y2):
            return

        # Initialize empty list for all pixel coordinates
        pixels: list[tuple[int, int]] = []
        pixels_append = pixels.append

        # Calculate interpolation factor for the middle point
        inv_slope02 = (x2 - x0) / (y2 - y0) if y2 != y0 else 0

        # First half of the triangle (bottom flat or top)
        if y1 == y0:  # Flat top triangle
            self._fill_flat_top_triangle(x0, y0, x1, y1, x2, y2, pixels_append)
        elif y1 == y2:  # Flat bottom triangle
            self._fill_flat_bottom_triangle(x0, y0, x1, y1, x2, y2, pixels_append)
        else:  # General triangle - split into flat-top and flat-bottom
            # Calculate the x-coordinate of the point on the long edge that has y = y1
            x3 = int(x0 + inv_slope02 * (y1 - y0))

            # Fill the flat bottom part
            self._fill_flat_bottom_triangle(x0, y0, x1, y1, x3, y1, pixels_append)

            # Fill the flat top part
            self._fill_flat_top_triangle(x1, y1, x3, y1, x2, y2, pixels_append)

        # Draw all pixels at once
        if pixels:
            self.set_pixels(pixels, "█", style)

    def _fill_flat_bottom_triangle(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        x2: int,
        y1_dup: int,
        pixels_append: Callable[[tuple[int, int]], None],
    ) -> None:
        """Helper method to fill a flat-bottom triangle (private method)."""
        dx1 = (x1 - x0) / (y1 - y0) if y1 != y0 else 0
        dx2 = (x2 - x0) / (y1 - y0) if y1 != y0 else 0

        # Initialize scanline coordinates
        x_start = x_end = float(x0)

        # Scan from top to bottom
        for y in range(y0, y1 + 1):
            # Add all pixels in this scanline
            for x in range(int(x_start), int(x_end) + 1):
                pixels_append((x, y))

            # Update scanline endpoints
            x_start += dx1
            x_end += dx2

    def _fill_flat_top_triangle(
        self,
        x0: int,
        y0: int,
        x1: int,
        y0_dup: int,
        x2: int,
        y2: int,
        pixels_append: Callable[[tuple[int, int]], None],
    ) -> None:
        """Helper method to fill a flat-top triangle (private method)."""
        dx1 = (x2 - x0) / (y2 - y0) if y2 != y0 else 0
        dx2 = (x2 - x1) / (y2 - y0) if y2 != y0 else 0

        # Initialize scanline coordinates
        x_start = float(x0)
        x_end = float(x1)

        # Scan from top to bottom
        for y in range(y0, y2 + 1):
            # Add all pixels in this scanline
            for x in range(int(x_start), int(x_end) + 1):
                pixels_append((x, y))

            # Update scanline endpoints
            x_start += dx1
            x_end += dx2

    def draw_filled_hires_triangle(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        hires_mode: HiResMode | None = None,
        style: str = "white",
    ) -> None:
        """Draw a filled high-resolution triangle using the specified style.
        Uses a scanline algorithm with subpixel precision.

        Args:
            x0: The x-coordinate of the first vertex.
            y0: The y-coordinate of the first vertex.
            x1: The x-coordinate of the second vertex.
            y1: The y-coordinate of the second vertex.
            x2: The x-coordinate of the third vertex.
            y2: The y-coordinate of the third vertex.
            hires_mode: The high-resolution mode to use.
            style: The style to apply to the characters.
        """
        # Use default hires mode if none provided
        hires_mode = hires_mode or self.default_hires_mode

        # Sort vertices by y-coordinate (y0 <= y1 <= y2)
        if y0 > y1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        if y1 > y2:
            x1, y1, x2, y2 = x2, y2, x1, y1
        if y0 > y1:
            x0, y0, x1, y1 = x1, y1, x0, y0

        # Skip if all points are the same or triangle has no height
        if abs(y0 - y2) < 1e-6:
            return

        # Initialize pixel collection
        pixels: list[tuple[float, float]] = []
        pixels_append = pixels.append

        # Define helper function to add a hi-res pixel
        def add_hires_pixel(x: float, y: float) -> None:
            pixels_append((x, y))

        # No edge parameters needed

        # Process based on triangle shape
        if abs(y1 - y0) < 1e-6:  # Flat top triangle
            self._fill_flat_top_hires_triangle(x0, y0, x1, y1, x2, y2, add_hires_pixel)
        elif abs(y1 - y2) < 1e-6:  # Flat bottom triangle
            self._fill_flat_bottom_hires_triangle(
                x0, y0, x1, y1, x2, y2, add_hires_pixel
            )
        else:  # General triangle - split into flat-top and flat-bottom
            # Calculate the interpolation factor for the split point
            t = (y1 - y0) / (y2 - y0)

            # Calculate the x-coordinate of the point on the long edge that has y = y1
            x3 = x0 + t * (x2 - x0)

            # Fill the flat bottom part
            self._fill_flat_bottom_hires_triangle(
                x0, y0, x1, y1, x3, y1, add_hires_pixel
            )

            # Fill the flat top part
            self._fill_flat_top_hires_triangle(x1, y1, x3, y1, x2, y2, add_hires_pixel)

        # Draw all hi-res pixels at once
        if pixels:
            self.set_hires_pixels(pixels, hires_mode, style)

    def _fill_flat_bottom_hires_triangle(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        x2: float,
        y1_dup: float,
        add_pixel: Callable[[float, float], None],
    ) -> None:
        """Helper method to fill a flat-bottom triangle with hi-res precision (private method)."""
        # Calculate slopes
        height = y1 - y0
        if abs(height) < 1e-6:
            return

        dx_left = (x1 - x0) / height
        dx_right = (x2 - x0) / height

        # Initialize scanline endpoints
        x_left = x0
        x_right = x0

        # Calculate steps for smoother rendering (use more y steps for better quality)
        y_steps = max(100, int(height * 10))
        y_step = height / y_steps

        # Scan from top to bottom
        for i in range(y_steps + 1):
            y = y0 + i * y_step

            # Calculate scanline width
            width = x_right - x_left

            # Calculate steps for this scanline
            x_steps = max(20, int(width * 10))
            x_step = width / max(1, x_steps)

            # Add pixels along scanline
            for j in range(x_steps + 1):
                x = x_left + j * x_step
                add_pixel(x, y)

            # Update scanline endpoints for next row
            x_left += dx_left * y_step
            x_right += dx_right * y_step

    def _fill_flat_top_hires_triangle(
        self,
        x0: float,
        y0: float,
        x1: float,
        y0_dup: float,
        x2: float,
        y2: float,
        add_pixel: Callable[[float, float], None],
    ) -> None:
        """Helper method to fill a flat-top triangle with hi-res precision (private method)."""
        # Calculate slopes
        height = y2 - y0
        if abs(height) < 1e-6:
            return

        dx_left = (x2 - x0) / height
        dx_right = (x2 - x1) / height

        # Initialize scanline endpoints
        x_left = x0
        x_right = x1

        # Calculate steps for smoother rendering (use more y steps for better quality)
        y_steps = max(100, int(height * 10))
        y_step = height / y_steps

        # Scan from top to bottom
        for i in range(y_steps + 1):
            y = y0 + i * y_step

            # Calculate scanline width
            width = x_right - x_left

            # Calculate steps for this scanline
            x_steps = max(20, int(width * 10))
            x_step = width / max(1, x_steps)

            # Add pixels along scanline
            for j in range(x_steps + 1):
                x = x_left + j * x_step
                add_pixel(x, y)

            # Update scanline endpoints for next row
            x_left += dx_left * y_step
            x_right += dx_right * y_step

    def draw_quad(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        x3: int,
        y3: int,
        style: str = "white",
    ) -> None:
        """Draw a quadrilateral outline using the specified style.

        Args:
            x0: The x-coordinate of the first vertex.
            y0: The y-coordinate of the first vertex.
            x1: The x-coordinate of the second vertex.
            y1: The y-coordinate of the second vertex.
            x2: The x-coordinate of the third vertex.
            y2: The y-coordinate of the third vertex.
            x3: The x-coordinate of the fourth vertex.
            y3: The y-coordinate of the fourth vertex.
            style: The style to apply to the characters.
        """
        # Draw the four sides of the quadrilateral
        self.draw_lines(
            [(x0, y0, x1, y1), (x1, y1, x2, y2), (x2, y2, x3, y3), (x3, y3, x0, y0)],
            "█",
            style,
        )

    def draw_hires_quad(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        x3: float,
        y3: float,
        hires_mode: HiResMode | None = None,
        style: str = "white",
    ) -> None:
        """Draw a high-resolution quadrilateral outline using the specified style.

        Args:
            x0: The x-coordinate of the first vertex.
            y0: The y-coordinate of the first vertex.
            x1: The x-coordinate of the second vertex.
            y1: The y-coordinate of the second vertex.
            x2: The x-coordinate of the third vertex.
            y2: The y-coordinate of the third vertex.
            x3: The x-coordinate of the fourth vertex.
            y3: The y-coordinate of the fourth vertex.
            hires_mode: The high-resolution mode to use.
            style: The style to apply to the characters.
        """
        # Draw the four sides of the quadrilateral with high-resolution
        self.draw_hires_lines(
            [(x0, y0, x1, y1), (x1, y1, x2, y2), (x2, y2, x3, y3), (x3, y3, x0, y0)],
            hires_mode,
            style,
        )

    def draw_filled_quad(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        x3: int,
        y3: int,
        style: str = "white",
    ) -> None:
        """Draw a filled quadrilateral using the specified style.
        Splits the quad into two triangles for filling.

        Args:
            x0: The x-coordinate of the first vertex.
            y0: The y-coordinate of the first vertex.
            x1: The x-coordinate of the second vertex.
            y1: The y-coordinate of the second vertex.
            x2: The x-coordinate of the third vertex.
            y2: The y-coordinate of the third vertex.
            x3: The x-coordinate of the fourth vertex.
            y3: The y-coordinate of the fourth vertex.
            style: The style to apply to the characters.
        """
        # Draw the quad as two filled triangles
        # First triangle (0, 1, 2)
        self.draw_filled_triangle(x0, y0, x1, y1, x2, y2, style)
        # Second triangle (0, 2, 3)
        self.draw_filled_triangle(x0, y0, x2, y2, x3, y3, style)

    def draw_filled_hires_quad(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        x3: float,
        y3: float,
        hires_mode: HiResMode | None = None,
        style: str = "white",
    ) -> None:
        """Draw a filled high-resolution quadrilateral using the specified style.
        Splits the quad into two triangles for filling.

        Args:
            x0: The x-coordinate of the first vertex.
            y0: The y-coordinate of the first vertex.
            x1: The x-coordinate of the second vertex.
            y1: The y-coordinate of the second vertex.
            x2: The x-coordinate of the third vertex.
            y2: The y-coordinate of the third vertex.
            x3: The x-coordinate of the fourth vertex.
            y3: The y-coordinate of the fourth vertex.
            hires_mode: The high-resolution mode to use.
            style: The style to apply to the characters.
        """
        # Draw the quad as two filled high-resolution triangles
        # First triangle (0, 1, 2)
        self.draw_filled_hires_triangle(x0, y0, x1, y1, x2, y2, hires_mode, style)
        # Second triangle (0, 2, 3)
        self.draw_filled_hires_triangle(x0, y0, x2, y2, x3, y3, hires_mode, style)

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
        # (x0, y0)     (x1, y0)
        #    ┌────────────┐
        #    │            │
        #    │            │
        #    │            │
        #    │            │
        #    └────────────┘
        # (x0, y1)     (x1, y1)

        # NOTE: A difference of 0 between coordinates results in a
        # width or height of 1 cell inside Textual.

        T = thickness
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))

        # Both width and height are 1. This would just be a dot, so
        # we don't draw anything.
        if (x1 - x0 == 0) and (y1 - y0 == 0):
            return

        # We now know either the width or height must be higher than 2.
        # Height is 1, place two horizontal line enders.
        if y1 - y0 == 0:
            self.set_pixel(x0, y0, char=get_box((0, T, 0, 0)), style=style)
            self.set_pixel(x1, y0, char=get_box((0, 0, 0, T)), style=style)
            if x1 - x0 >= 2:
                # Width is greater than or equal to 3, draw a horizontal line
                # between the line enders.
                self.draw_line(
                    x0 + 1, y0, x1 - 1, y1, char=get_box((0, T, 0, T)), style=style
                )
            return

        # Width is 1, place two vertical line enders.
        if x1 - x0 == 0:
            self.set_pixel(x0, y0, char=get_box((0, 0, T, 0)), style=style)
            self.set_pixel(x0, y1, char=get_box((T, 0, 0, 0)), style=style)
            if y1 - y0 >= 2:
                # Height is greater than or equal to 3, draw a horizontal line
                # between the line enders.
                self.draw_line(
                    x0, y0 + 1, x1, y1 - 1, char=get_box((T, 0, T, 0)), style=style
                )
            return

        # The remaining conditions require all the corner pieces to be drawn.
        self.set_pixel(x0, y0, char=get_box((0, T, T, 0)), style=style)
        self.set_pixel(x1, y0, char=get_box((0, 0, T, T)), style=style)
        self.set_pixel(x1, y1, char=get_box((T, 0, 0, T)), style=style)
        self.set_pixel(x0, y1, char=get_box((T, T, 0, 0)), style=style)

        # If width and height are both 2, we don't need any lines. Only corners.
        if (x1 - x0 == 1) and (y1 - y0 == 1):
            return

        # Width is greater than or equal to 3, draw horizontal lines.
        if x1 - x0 >= 2:
            for y in y0, y1:
                self.draw_line(
                    x0 + 1, y, x1 - 1, y, char=get_box((0, T, 0, T)), style=style
                )
        # Height is greater than or equal to 3, draw vertical lines.
        if y1 - y0 >= 2:
            for x in x0, x1:
                self.draw_line(
                    x, y0 + 1, x, y1 - 1, char=get_box((T, 0, T, 0)), style=style
                )

    def draw_filled_circle(
        self, cx: int, cy: int, radius: int, style: str = "white"
    ) -> None:
        """Draw a filled circle using Bresenham's algorithm. Compensates for 2:1 aspect ratio.

        Args:
            cx (int): X-coordinate of the center of the circle.
            cy (int): Y-coordinate of the center of the circle.
            radius (int): Radius of the circle.
            style (str): Style of the pixels to be drawn.
        """
        # Early rejection for invalid inputs
        if radius <= 0:
            return

        # Initialize buffer to collect all pixels
        pixels: list[tuple[int, int]] = []
        pixels_append = pixels.append  # Local reference for faster calls

        x = 0
        y = radius
        d = 3 - 2 * radius

        # Pre-compute aspect ratio adjustments
        max_iterations = radius * 2  # Safety limit
        iteration = 0

        while y >= x and iteration < max_iterations:
            # Adjust y-coordinates to account for 2:1 aspect ratio
            y1 = cy + (y + 1) // 2
            y2 = cy + (x + 1) // 2
            y3 = cy - x // 2
            y4 = cy - y // 2

            # Add horizontal lines of pixels
            for xpos in range(cx - x, cx + x + 1):
                pixels_append((xpos, y1))
                pixels_append((xpos, y4))

            for xpos in range(cx - y, cx + y + 1):
                pixels_append((xpos, y2))
                pixels_append((xpos, y3))

            x += 1
            if d > 0:
                y -= 1
                d = d + 4 * (x - y) + 10
            else:
                d = d + 4 * x + 6

            iteration += 1

        # Draw all pixels at once
        if pixels:
            self.set_pixels(pixels, "█", style)

    def draw_filled_hires_circle(
        self,
        cx: float,
        cy: float,
        radius: float,
        hires_mode: HiResMode | None = None,
        style: str = "white",
    ) -> None:
        """Draw a filled circle, with high-resolution support.

        Args:
            cx (float): X-coordinate of the center of the circle.
            cy (float): Y-coordinate of the center of the circle.
            radius (float): Radius of the circle.
            hires_mode (HiResMode): The high-resolution mode to use.
            style (str): Style of the pixels to be drawn.
        """
        # Early rejection for invalid inputs
        if radius <= 0:
            return

        # Constants and scaling factors
        scale_x = 1
        scale_y = 2
        aspect_ratio = scale_x / scale_y

        # Pre-compute values used in the inner loop
        radius_squared = radius**2
        inv_scale_x = 1.0 / scale_x
        inv_scale_y_aspect = 1.0 / (scale_y * aspect_ratio)

        # Determine the bounding box for the circle
        y_min = int(-radius * scale_y)
        y_max = int(radius * scale_y) + 1
        x_min = int(-radius * scale_x)
        x_max = int(radius * scale_x) + 1

        # Initialize an empty list for collecting pixel coordinates
        # (We calculate estimated_pixels only for the safety check below)
        estimated_pixels = int(3.2 * radius * radius)  # 3.2 instead of π for safety
        pixels: list[tuple[float, float]] = []
        pixels_append = pixels.append  # Local reference for faster calls

        # Use a more efficient scanning algorithm
        # For each y, compute the range of valid x values directly
        for y in range(y_min, y_max):
            # Solve circle equation for x: (x/sx)² + (y/(sy*ar))² <= r²
            y_term = (y * inv_scale_y_aspect) ** 2
            if y_term > radius_squared:
                continue  # Skip this row if y is outside the circle

            x_term_max = radius_squared - y_term
            if x_term_max < 0:
                continue  # Skip if no valid x values

            # Find the range of valid x values
            x_radius = int((x_term_max**0.5) * scale_x)
            x_start = max(x_min, -x_radius)
            x_end = min(x_max, x_radius + 1)

            # Add all points in this row in one go
            for x in range(x_start, x_end):
                pixels_append((cx + x * inv_scale_x, cy + y / scale_y))

            # Safety check
            if len(pixels) > estimated_pixels * 2:
                break

        # Render all pixels at once
        self.set_hires_pixels(pixels, hires_mode, style)

    def draw_circle(self, cx: int, cy: int, radius: int, style: str = "white") -> None:
        """Draw a circle using Bresenham's algorithm. Compensates for 2:1 aspect ratio.

        Args:
            cx (int): X-coordinate of the center of the circle.
            cy (int): Y-coordinate of the center of the circle.
            radius (int): Radius of the circle.
            style (str): Style of the pixels to be drawn.
        """
        # Early rejection for invalid inputs
        if radius <= 0:
            return

        # Initialize buffer to collect all pixels
        pixels: list[tuple[int, int]] = []
        pixels_append = pixels.append  # Local reference for faster calls

        x = radius
        y = 0
        decision = 1 - radius

        # Pre-compute aspect ratio adjustments
        max_iterations = radius * 2  # Safety limit
        iteration = 0

        while y <= x and iteration < max_iterations:
            y_half = y // 2
            x_half = x // 2

            # Add all 8 points in each octant
            pixels_append((cx + x, cy + y_half))
            pixels_append((cx - x, cy + y_half))
            pixels_append((cx + x, cy - y_half))
            pixels_append((cx - x, cy - y_half))
            pixels_append((cx + y, cy + x_half))
            pixels_append((cx - y, cy + x_half))
            pixels_append((cx + y, cy - x_half))
            pixels_append((cx - y, cy - x_half))

            y += 1
            if decision <= 0:
                decision += 2 * y + 1
            else:
                x -= 1
                decision += 2 * (y - x) + 1

            iteration += 1

        # Draw all pixels at once
        if pixels:
            self.set_pixels(pixels, "█", style)

    def draw_hires_circle(
        self,
        cx: float,
        cy: float,
        radius: float,
        hires_mode: HiResMode | None = None,
        style: str = "white",
    ) -> None:
        """Draw a circle with high-resolution support using Bresenham's algorithm. Compensates for 2:1 aspect ratio.

        Args:
            cx (float): X-coordinate of the center of the circle.
            cy (float): Y-coordinate of the center of the circle.
            radius (float): Radius of the circle.
            hires_mode (HiResMode): The high-resolution mode to use.
            style (str): Style of the pixels to be drawn.
        """
        # Early rejection for invalid inputs
        if radius <= 0:
            return

        # Initialize an empty list for collecting pixel coordinates
        # (We calculate estimated_size only for the safety check below)
        estimated_size = int(
            radius * 16
        )  # Each step adds 8 pixels, estimate 4*radius steps
        pixels: list[tuple[float, float]] = []
        pixels_extend = pixels.extend  # Local reference for faster calls

        # Pre-compute constants
        scale_x = 1
        scale_y = 2
        aspect_ratio = scale_x / scale_y

        # Midpoint circle algorithm with floating point precision
        x: float = radius
        y: float = 0
        decision: float = 1 - radius

        # Pre-compute points for each octant to avoid repeated calculations
        def get_circle_points(x: float, y: float) -> list[tuple[float, float]]:
            y_scaled = y * aspect_ratio
            x_scaled = x * aspect_ratio
            return [
                (cx + x, cy + y_scaled),
                (cx - x, cy + y_scaled),
                (cx + x, cy - y_scaled),
                (cx - x, cy - y_scaled),
                (cx + y, cy + x_scaled),
                (cx - y, cy + x_scaled),
                (cx + y, cy - x_scaled),
                (cx - y, cy - x_scaled),
            ]

        # Generate points for the circle
        while y <= x:
            # Add all 8 points at once
            pixels_extend(get_circle_points(x, y))

            # Update position
            y += 0.5
            if decision <= 0:
                decision += 2 * y + 1
            else:
                x -= 0.5
                decision += 2 * (y - x) + 1

            # Safety check to avoid infinite loops
            if len(pixels) > estimated_size:
                break

        # Render all pixels at once
        self.set_hires_pixels(pixels, hires_mode, style)

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
    ) -> list[tuple[int, int]]:
        """Get all pixel coordinates on the line between two points.

        Fast implementation of Bresenham's line algorithm.
        Returns a list of coordinates instead of a generator for better performance.

        Args:
            x0: starting point x coordinate
            y0: starting point y coordinate
            x1: end point x coordinate
            y1: end point y coordinate

        Returns:
            List of (x, y) coordinate tuples that make up the line.
        """
        # Early rejection if endpoints are identical
        if x0 == x1 and y0 == y1:
            return [(x0, y0)]

        # Fast path for horizontal lines
        if y0 == y1:
            if x0 < x1:
                return [(x, y0) for x in range(x0, x1 + 1)]
            else:
                return [(x, y0) for x in range(x1, x0 + 1)]

        # Fast path for vertical lines
        if x0 == x1:
            if y0 < y1:
                return [(x0, y) for y in range(y0, y1 + 1)]
            else:
                return [(x0, y) for y in range(y1, y0 + 1)]

        # Initialize algorithm variables
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        error = dx + dy

        # Pre-allocate result list with known line length for efficiency
        # The +1 ensures we have enough space for all points
        max_points = max(abs(x1 - x0), abs(y1 - y0)) + 1
        points = []
        points.append((x0, y0))

        # x and y are mutable copies so we can modify them
        x, y = x0, y0

        # Main loop - more efficient without generator overhead
        while not (x == x1 and y == y1):
            e2 = 2 * error
            if e2 >= dy:
                if x == x1:
                    break
                error += dy
                x += sx
            if e2 <= dx:
                if y == y1:
                    break
                error += dx
                y += sy
            points.append((x, y))

            # Safety check to avoid infinite loops
            if len(points) > max_points:
                break

        return points
