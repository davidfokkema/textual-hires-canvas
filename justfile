# Run the demo.
demo:
    uv run textual run textual_hires_canvas.demo:DemoApp

# List all examples.
list-examples:
    ls docs/examples

# Run an example in docs/examples. Usage: just example minimal.py
example script:
    uv run docs/examples/{{script}}

# Check project's types.
typecheck:
    uv run mypy -p textual_hires_canvas --strict

# Test the project.
test:
    uv run pytest

# Format the project.
format:
    uvx ruff format

# Fix formatting issues.
fix:
    uvx ruff check --fix

# Build the documentation.
docs:
    uv run mkdocs build

# Serve the documentation.
serve:
    uv run mkdocs serve

# Deploy the documentation to GitHub Pages.
deploy-docs:
    uv run mkdocs gh-deploy --force
