demo:
    uv run textual run textual_hires_canvas.demo:DemoApp

# Run an example in docs/examples. Usage: just example minimal.py
example script:
    uv run docs/examples/{{script}}

typecheck:
    uv run mypy -p textual_hires_canvas --strict

test:
    uv run pytest

format:
    uvx ruff format

fix:
    uvx ruff check --fix
