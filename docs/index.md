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

## Air Quality

Beyond SJVAir's own fleet, the CLI and client can filter monitors by these integrated networks with `--device`:

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} {far}`cloud;sd-mr-1 fa-lg` PurpleAir
:link: client/resources/monitors
:link-type: doc
:link-alt: Filtering by device

Community-operated network of low-cost consumer PM2.5 sensors.

`--device PurpleAir`
:::

:::{grid-item-card} {far}`shield-check;sd-mr-1 fa-lg` AirNow
:link: client/resources/monitors
:link-type: doc
:link-alt: Filtering by device

EPA's national real-time feed of regulatory-grade air monitors.

`--device AirNow`
:::

:::{grid-item-card} {far}`eye;sd-mr-1 fa-lg` AQview
:link: client/resources/monitors
:link-type: doc
:link-alt: Filtering by device

CARB's public viewer aggregating California's community monitoring networks.

`--device AQview`
:::

:::{grid-item-card} {far}`weight-hanging;sd-mr-1 fa-lg` BAM1022
:link: client/resources/monitors
:link-type: doc
:link-alt: Filtering by device

Met One BAM-1022 beta attenuation monitors — regulatory-grade PM.

`--device BAM1022`
:::

:::{grid-item-card} {far}`smog;sd-mr-1 fa-lg` AQLite
:link: client/resources/monitors
:link-type: doc
:link-alt: Filtering by device

2B Technologies AQLite regulatory-grade ozone (O3) monitors.

`--device AQLite`
:::

:::{grid-item-card} {far}`box-open;sd-mr-1 fa-lg` AirGradient
:link: client/resources/monitors
:link-type: doc
:link-alt: Filtering by device

Open-source air quality monitor hardware.

`--device AirGradient`
:::

:::{grid-item-card} {far}`people-group;sd-mr-1 fa-lg` VOZBox
:link: client/resources/monitors
:link-type: doc
:link-alt: Filtering by device

Community-deployed air monitors.

`--device VOZBox`
:::

::::

## Other Datasets

Beyond SJVAir's own network of air quality monitors, the CLI and client can pull in several third-party datasets:

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} {far}`gauge-high;sd-mr-1 fa-lg` CalEnviroScreen
:link: cli/data-export/calenviroscreen
:link-type: doc

OEHHA / CalEPA cumulative pollution-burden scores by census tract.

`sjvair calenviroscreen5`
:::

:::{grid-item-card} {far}`temperature-high;sd-mr-1 fa-lg` CalHeatScore
:link: cli/data-export/calheatscore
:link-type: doc

CalEPA daily ZIP-code-level heat-risk scores for the San Joaquin Valley.

`sjvair calheatscore`
:::

:::{grid-item-card} {far}`industry;sd-mr-1 fa-lg` Facility Emissions
:link: cli/data-export/ceidars
:link-type: doc

CARB permitted stationary emissions sources (facilities).

`sjvair ceidars`
:::

:::{grid-item-card} {far}`fire;sd-mr-1 fa-lg` Fire & Smoke
:link: cli/data-export/hms
:link-type: doc

NOAA satellite-derived smoke plume and fire detections.

`sjvair hms`
:::

:::{grid-item-card} {far}`spray-can-sparkles;sd-mr-1 fa-lg` Pesticides
:link: cli/data-export/pesticides
:link-type: doc

CDPR mandatory agricultural pesticide use reports.

`sjvair pesticides`
:::

:::{grid-item-card} {far}`chart-line;sd-mr-1 fa-lg` Forecasts
:link: cli/data-export/forecasts
:link-type: doc

SJVAPCD daily air quality forecasts by San Joaquin Valley county zone.

`sjvair forecasts`
:::

:::{grid-item-card} {far}`cloud-sun;sd-mr-1 fa-lg` CIMIS
:link: client/resources/monitors
:link-type: doc
:link-alt: Filtering by device

California's irrigation-management weather station network — also the source of SJVAir's meteorological entry types.

`--device CIMIS`
:::

::::

---

Released under the [MIT License](license.md).

```{toctree}
:caption: Commands
:hidden:

cli/usage
cli/troubleshooting
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
