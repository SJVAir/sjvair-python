# Pesticides

California Department of Pesticide Regulation (CDPR) data. Pick a dataset with `--type`:

| `--type` | Data |
|---|---|
| `chemicals` | Chemical reference list |
| `commodities` | Commodity reference list |
| `products` | Product reference list |
| `use` | Pesticide use reports (region filter optional) |
| `notice` | Notice-of-intent reports (region filter optional) |
| `region-use` | Use aggregated for one region (region filter required) |
| `region-notice` | Notices aggregated for one region (region filter required) |
| `region-summary` | Summary totals for one region (region filter required) |

```bash
sjvair pesticides --type chemicals
```

```bash
sjvair pesticides --type products --output products.csv
```

```bash
sjvair pesticides --type use --county Fresno
```

```bash
sjvair pesticides --type region-summary --county Fresno
```
