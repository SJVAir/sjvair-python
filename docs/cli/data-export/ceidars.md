# Facility Emissions

CEIDARS (California Emissions Inventory Development and Reporting System) data on permitted stationary emissions sources — name, location, SIC code, and minor/major source status.

## `ceidars`

Scope to a single region with `--county`, `--city`, `--zip`, `--tract` (FIPS), `--urban`, or `--region-id` — at most one. Omit the region filter to export every facility in the dataset.

```bash
sjvair ceidars
```

```bash
sjvair ceidars --county Kern --output kern-facilities.csv
```

```bash
sjvair ceidars --zip 93706 --format json
```
