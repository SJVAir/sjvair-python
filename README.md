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
