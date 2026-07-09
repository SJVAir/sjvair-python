:layout: landing

# SJVAir Toolkit

Command-line tool and Python client for [SJVAir](https://www.sjvair.com/) — a network of air
quality monitors across California's San Joaquin Valley.

## Install

```bash
pip install sjvair
```

Map and timelapse generation need the optional `maps` extra (`pip install sjvair[maps]`) plus `ffmpeg` on `PATH` for timelapse videos — see [Map generation](cli/maps/index.md).

## Where to next

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} {octicon}`terminal;1.2em;sd-mr-1` Commands
:link: cli/usage
:link-type: doc

Bulk data export, static maps, and timelapse videos from the command line.
:::

:::{grid-item-card} {octicon}`code;1.2em;sd-mr-1` Python
:link: client/usage
:link-type: doc

Scriptable access to monitors, regions, and every integrated dataset.
:::
::::

## Datasets

Beyond SJVAir's own network of air quality monitors, the CLI and client can pull in several third-party datasets:

| Dataset | Source | Coverage |
|---|---|---|
| [CalEnviroScreen](cli/data-export/calenviroscreen.md) | OEHHA / CalEPA | Cumulative pollution-burden scores by census tract |
| [Facility Emissions](cli/data-export/ceidars.md) | CARB | Permitted stationary emissions sources (facilities) |
| [Fire & Smoke](cli/data-export/hms.md) | NOAA | Satellite-derived smoke plume and fire detections |
| [Pesticides](cli/data-export/pesticides.md) | CDPR | Mandatory agricultural pesticide use reports |

---

Released under the [MIT License](license.md).

```{toctree}
:caption: Commands
:hidden:

cli/usage
cli/data-export/index
cli/maps/index
```

```{toctree}
:caption: Python
:hidden:

client/usage
client/resources/index
client/bulk-export
client/maps
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
License <license>
```
