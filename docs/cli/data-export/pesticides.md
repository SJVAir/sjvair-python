# Pesticides

California Department of Pesticide Regulation (CDPR) reference lists and use/notice reports. Pick a dataset with `--type`:

| `--type` | Data | Region filter |
|---|---|---|
| `chemicals` | Chemical (active ingredient) reference list | ignored |
| `commodities` | Commodity (crop) reference list | ignored |
| `products` | Registered product reference list | ignored |
| `use` | Pesticide use reports | optional |
| `notice` | Notice-of-intent reports | optional |
| `region-use` | Use reports aggregated for one region | required |
| `region-notice` | Notices aggregated for one region | required |
| `region-summary` | Summary totals for one region | required |

Region filters — `--county`, `--city`, `--zip`, `--tract` (FIPS), `--urban`, `--region-id`, at most one — only take effect for `use`, `notice`, and the `region-*` types. Passing one with `chemicals`, `commodities`, or `products` is silently ignored (an invalid or ambiguous value still errors).

## Reference lists

```bash
sjvair pesticides --type chemicals
```

```bash
sjvair pesticides --type products --output products.csv
```

## Use and notice reports

```bash
sjvair pesticides --type use --county Fresno --output use-fresno.csv
```

```bash
sjvair pesticides --type notice --zip 93706
```

Without a region filter, `use`/`notice` return every report in the dataset.

## Region aggregates

`region-use`, `region-notice`, and `region-summary` require exactly one region filter.

```bash
sjvair pesticides --type region-use --county Fresno --output fresno-use.csv
```

```bash
sjvair pesticides --type region-notice --county Fresno
```

```bash
sjvair pesticides --type region-summary --county Fresno
```

`region-summary` always prints indented JSON to stdout — `--output` and `--format` are ignored.
