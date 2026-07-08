# SJVAir Toolkit

Command-line tool and Python client for [SJVAir](https://www.sjvair.com/) — a network of air
quality monitors across California's San Joaquin Valley.

## Install

```bash
pip install sjvair
```

## Quickstart

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    for monitor in client.monitors.list():
        print(f"{monitor['id']}: {monitor['name']}")
```

```bash
sjvair monitors list --county Fresno --output fresno.csv
```

## Where to next

- **[CLI guide](cli/guide.md)** / **[CLI reference](cli/reference.md)**
- **[Python client guide](client/guide.md)** / **[API reference](client/reference.md)**

```{toctree}
:hidden:
:maxdepth: 2

cli/guide
cli/reference
client/guide
client/reference
changelog
```
