import numpy as np
from textual import on
from textual.app import App, ComposeResult

from textual_hires_canvas import Canvas, HiResMode


class RotatingCubeApp(App[None]):
    def compose(self) -> ComposeResult:
        yield Canvas()

    def on_mount(self) -> None:
        self.edges = [
            (0, 1),
            (1, 3),
            (3, 2),
            (2, 0),
            (4, 5),
            (5, 7),
            (7, 6),
            (6, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        ]
        # Define cube vertices (centered at origin)
        h = 12  # Half size of the cube
        cube_vertices = np.array(
            [
                [-h, -h, -h],
                [h, -h, -h],
                [-h, h, -h],
                [h, h, -h],
                [-h, -h, h],
                [h, -h, h],
                [-h, h, h],
                [h, h, h],
            ]
        )
        self.vertices_generator = update(cube_vertices)
        self.set_interval(1 / 10, self.draw_cube)

    @on(Canvas.Resize)
    def resize_canvas(self, event: Canvas.Resize) -> None:
        event.canvas.reset(size=event.size)

    def draw_cube(self):
        """Draws the rotating cube on a given Canvas object."""
        canvas = self.query_one(Canvas)
        canvas.reset()
        width = canvas.size.width
        height = canvas.size.height

        projected_vertices = next(self.vertices_generator)
        for edge in self.edges:
            x0, y0 = projected_vertices[edge[0]]
            x1, y1 = projected_vertices[edge[1]]
            canvas.draw_hires_line(
                x0 + width / 2,
                y0 + height / 2,
                x1 + width / 2,
                y1 + height / 2,
                hires_mode=HiResMode.BRAILLE,
                style="#ffff00",
            )


def rotation_matrix_y(angle):
    """Creates a 3D rotation matrix for rotation around the Y-axis."""
    return np.array(
        [
            [np.cos(angle), 0, np.sin(angle)],
            [0, 1, 0],
            [-np.sin(angle), 0, np.cos(angle)],
        ]
    )


def rotation_matrix_x(angle):
    """Creates a 3D rotation matrix for rotation around the X-axis."""
    return np.array(
        [
            [1, 0, 0],
            [0, np.cos(angle), -np.sin(angle)],
            [0, np.sin(angle), np.cos(angle)],
        ]
    )


def apply_perspective(vertices, d=30):
    """Applies a simple perspective projection to 3D vertices."""
    projected = []
    for x, y, z in vertices:
        factor = d / (d + z)  # Perspective factor
        projected.append((x * factor, y * factor))
    return np.array(projected)


def update(vertices):
    """Generator that yields rotated and projected vertices."""
    distance = 10
    num = 0
    while True:
        angle_y = num * np.pi / 30  # Rotating stepwise around Y-axis
        angle_x = num * np.pi / 60  # Rotating stepwise around X-axis
        rot_matrix = np.dot(rotation_matrix_x(angle_x), rotation_matrix_y(angle_y))
        rotated_vertices = np.dot(vertices, rot_matrix.T)
        rotated_vertices[:, 1] /= 2  # Correct for cell aspect ratio
        rotated_vertices[:, 2] += distance  # Move cube forward
        projected_vertices = apply_perspective(rotated_vertices)
        yield projected_vertices
        num += 1


if __name__ == "__main__":
    RotatingCubeApp().run()
