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

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} {octicon}`terminal;1.2em;sd-mr-1` Commands
:link: cli/quickstart
:link-type: doc

Bulk data export, static maps, and timelapse videos from the command line.
:::

:::{grid-item-card} {octicon}`code;1.2em;sd-mr-1` Python
:link: client/quickstart
:link-type: doc

Scriptable access to monitors, regions, and every integrated dataset.
:::
::::

## Datasets

Beyond SJVAir's own network of air quality monitors, the CLI and client can pull in several third-party datasets:

| Dataset | Source | Coverage |
|---|---|---|
| [CalEnviroScreen](cli/data-export/calenviroscreen.md) | OEHHA / CalEPA | Cumulative pollution-burden scores by census tract |
| [CEIDARS](cli/data-export/ceidars.md) | CARB | Permitted stationary emissions sources (facilities) |
| [HMS](cli/data-export/hms.md) | NOAA | Satellite-derived smoke plume and fire detections |
| [Pesticides](cli/data-export/pesticides.md) | CDPR | Mandatory agricultural pesticide use reports |

```{toctree}
:caption: Commands
:hidden:

Quickstart <cli/quickstart>
cli/data-export/index
cli/maps/index
```

```{toctree}
:caption: Python
:hidden:

Quickstart <client/quickstart>
Resources <client/resources/index>
Bulk export <client/bulk-export>
Maps <client/maps>
Output formats <client/output-formats>
Configuration <client/configuration>
```

```{toctree}
:caption: Reference
:hidden:

Commands <cli/reference>
Python <client/reference>
REST API <api/reference>
```

```{toctree}
:hidden:

Changelog <changelog>
```
