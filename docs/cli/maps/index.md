# Generating Maps

Commands for rendering air quality data as static map images or timelapse videos. Both require `pip install sjvair[maps]` (matplotlib, contextily, geopandas, shapely) and share the same `--region`/`--buffer`/`--bbox`/`--scope` area options.

| Command | Produces |
|---|---|
| [Static maps](static.md) | A single static PNG, live or as of a historical timestamp |
| [Timelapse videos](timelapse.md) | An MP4 assembled from a sequence of historical frames |

```{toctree}
:hidden:

static
timelapse
```
