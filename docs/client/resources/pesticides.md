# Pesticides — `client.pesticides`

California Department of Pesticide Regulation (CDPR) reference lists and use/notice reports.

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    use = list(client.pesticides.use.list(county='Fresno'))
    print(use[0])
```

```python
{
    "id": 5820134,
    "year": 2023,
    "use_no": 1847213,
    "comtrs": "060190010S26E14",
    "lbs_chemical": 42.6,
    "acres_treated": 18.0,
    "application_date": "2023-06-14",
    "aerial_ground": "G",
    "county": {"name": "Fresno"},
    "product": {"name": "ROUNDUP PROMAX"},
    "chemical": {"name": "GLYPHOSATE, POTASSIUM SALT"},
    "commodity": {"name": "ALMOND"},
}
```

## Methods

| Method | Description |
|---|---|
| `chemicals.list(**params)` / `chemicals.get(id)` | Chemical reference list |
| `commodities.list(**params)` / `commodities.get(id)` | Commodity reference list |
| `products.list(**params)` / `products.get(id)` | Product reference list |
| `use.list(**params)` | Pesticide use reports (region filter optional) |
| `notice.list(**params)` | Notice-of-intent reports (region filter optional) |
| `region_use(region_id, **params)` | Use aggregated for one region |
| `region_notice(region_id, **params)` | Notices aggregated for one region |
| `region_summary(region_id, **params)` | Summary totals for one region |

```python
# Total pounds of chemical applied in a region, by product
summary = client.pesticides.region_summary(region_id='gY8kw2')
print(summary)
```

```python
{
    "region_id": "gY8kw2",
    "total_lbs_chemical": 184_230.5,
    "total_acres_treated": 61_402.0,
    "report_count": 3841,
}
```
