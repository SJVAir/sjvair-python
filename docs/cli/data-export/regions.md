# Regions

## `regions list`

Regions of a given `--type`. Types: `county`, `city`, `zipcode`, `tract`, `cdp`, `place`, `urban_area`, `congressional_district`, `state_assembly`, `state_senate`, `school_district`, `land_use`, `protected`, `mtrs`, `custom`.

```bash
sjvair regions list --type county
```

```bash
sjvair regions list --type city --county Fresno --output cities.csv
```

## `regions search`

Search regions by name — useful for finding a region's ID, or for seeing every candidate up front when a shortcut flag (`--county`/`--city`/`--zip`/`--tract`/`--urban`) would otherwise fail with an "Ambiguous region" error. Prints a table by default; pass `--output` or `--format` for CSV/JSON/YAML instead.

Without `--type`, searches the same 5 types the shortcut flags resolve to (`county`, `city`, `zipcode`, `tract`, `urban_area`):

```bash
sjvair regions search Hanford
```

```
  77yxc                                 city          Hanford
  crnag                                 city          Waterford
  zvnca                                 urban_area    Hanford
  k3net                                 urban_area    Waterford
```

Scope to one type:

```bash
sjvair regions search Fresno --type county
```

Search every region type, including ones the shortcut flags never use (`protected`, `school_district`, etc.):

```bash
sjvair regions search Hanford --type all
```

Get structured output instead of the table:

```bash
sjvair regions search Hanford --format csv
```

## `regions get`

A single region by its ID.

```bash
sjvair regions get gY8kw2
```

## `regions summaries`

Aggregated statistics for one region. Requires `--type`, `--resolution`, `--start-date`, `--end-date`, and exactly one region filter. Each row is tagged with its `region_id`.

::::{tabs}

:::{code-tab} bash
sjvair regions summaries \
  --type pm25 --resolution monthly \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --county Fresno --output fresno-monthly.csv
:::

:::{code-tab} powershell
sjvair regions summaries `
  --type pm25 --resolution monthly `
  --start-date 2022-01-01 --end-date 2022-12-31 `
  --county Fresno --output fresno-monthly.csv
:::

::::
