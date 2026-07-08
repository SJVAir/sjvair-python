# regions

**`regions list`** — regions of a given `--type`. Types: `county`, `city`, `zipcode`, `tract`, `cdp`, `place`, `urban_area`, `congressional_district`, `state_assembly`, `state_senate`, `school_district`, `land_use`, `protected`, `mtrs`, `custom`.

```bash
sjvair regions list --type county
sjvair regions list --type city --county Fresno --output cities.csv
```

**`regions get`** — a single region by its sqid.

```bash
sjvair regions get gY8kw2
```

**`regions summaries`** — aggregated statistics for one region. Requires `--type`, `--resolution`, `--start-date`, `--end-date`, and exactly one region filter. Each row is tagged with its `region_id`.

```bash
sjvair regions summaries \
  --type pm25 --resolution monthly \
  --start-date 2022-01-01 --end-date 2022-12-31 \
  --county Fresno --output fresno-monthly.csv
```
