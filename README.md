# sjvair

Command-line tool and Python client for [SJVAir](https://www.sjvair.com/) — a network of air quality monitors across California's San Joaquin Valley.

📖 **Full documentation: https://SJVAir.github.io/sjvair-python/**

```bash
pip install sjvair
```

## Quickstart

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    for monitor in client.monitors.list():
        print(monitor['id'], monitor['name'])
```

```bash
sjvair monitors list --county Fresno --output fresno.csv
sjvair regions list --type county
```

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run tests (live tests hit the real API and are excluded by default)
uv run pytest
uv run pytest -m live      # run the live integration tests

# Lint and format
uv run ruff check sjvair/
uv run ruff format sjvair/

# Type check
uv run ty check sjvair/
```

### Documentation

Docs are built with [Sphinx](https://www.sphinx-doc.org/) + [MyST](https://myst-parser.readthedocs.io/) and deployed to GitHub Pages on every push to `main`.

```bash
# Install with docs dependencies
uv sync --group docs

# Build once (output in docs/_build/html)
uv run sphinx-build -b html docs docs/_build/html

# Build, serve, and auto-rebuild on change
uv run sphinx-autobuild docs docs/_build/html --port 8080
```
