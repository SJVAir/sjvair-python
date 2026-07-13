# TEMPO

NASA TEMPO satellite air-quality data. Pick a query with `--type`:

| `--type` | Data | Requires |
|---|---|---|
| `products` | Product metadata (label, units, legend) | — |
| `granules` | Granule list for one product | `--product` |
| `latest` | Most recent granule for one product | `--product` |
| `point` | Hourly point-value series at a coordinate | `--product`, `--lat`, `--lon` |
| `region` | Hourly zonal-stats series over a region | `--product`, one region flag |

`--product` is one of `no2`, `o3tot`, `hcho`, `cldo4`.

## Products and latest granule

```bash
sjvair tempo --type products
```

```bash
sjvair tempo --type latest --product no2
```

## Granules

```bash
sjvair tempo --type granules --product no2 --output no2-today.csv
```

```bash
sjvair tempo --type granules --product hcho --date 2026-07-10 --is-final
```

## Point series

```bash
sjvair tempo --type point --product no2 --lat 36.7468 --lon -119.7726
```

```bash
sjvair tempo --type point --product no2 --lat 36.7468 --lon -119.7726 --start 2026-07-01 --end 2026-07-02
```

## Region series

Region filters — `--county`, `--city`, `--zip`, `--tract` (FIPS), `--urban`, `--region-id` — at most one, required for `--type region`.

```bash
sjvair tempo --type region --product no2 --county Fresno
```
