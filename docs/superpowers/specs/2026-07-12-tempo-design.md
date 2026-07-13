# TEMPO satellite data client support

## Context

sjvair.com PR 248 (TEMPO) previously had no API layer — its own description
explicitly deferred `camp/api/v2/tempo/` as "out of scope." That's now landed
(PR description is stale but the file list and diff confirm it). This is a
real, five-endpoint API surface, larger than the CES5/CalHeatScore or
monitors device-filter rounds.

**Products:** `no2`, `o3tot`, `hcho`, `cldo4` — all four are valid values for
`granules`/`point`/`region` queries. `cldo4` is excluded only from the
product-metadata endpoint (QA-only, not a user-facing map layer).

**Endpoints** (base path `tempo/`):

| Path | Shape | Notes |
|---|---|---|
| `GET /tempo/` | plain list | Product metadata: `key`, `label`, `units`, `legend` (color stops). Excludes `cldo4`. |
| `GET /tempo/<product>/granules/` | paginated list | `sqid`, `timestamp`, `is_final`, `version`, `bounds`, `preview_url`. Filters: `date`, `timestamp`(+`__lt`/`__lte`/`__gt`/`__gte`), `is_final`, `version`(+`__iexact`). Defaults to today (America/Los_Angeles), falling back to yesterday if before noon and today has no data yet. |
| `GET /tempo/<product>/granules/latest/` | single object | Most recent granule, same fields as above. 404 if none exist yet. |
| `GET /tempo/<product>/point/?latitude=&longitude=&start=&end=` | plain list | Hourly point-value series: `timestamp`, `is_final`, `version`, `value` (pixel value at the coordinate, `None` = masked/nodata, not a missing hour). `start`/`end` optional ISO 8601 timestamps (naive treated as `America/Los_Angeles`); omitting both defaults to today's available granules' min/max timestamp. Max range 90 days. |
| `GET /tempo/<product>/region/<region_id>/?start=&end=` | plain list | Hourly zonal-stats series over a region boundary (`region_id` = region sqid): `timestamp`, `is_final`, `version`, `count`, `sum`, `mean`, `stddev`, `min`, `max`. Same `start`/`end` semantics as `point`. |

The backend PR is still open/unmerged; building against its current diff per
the established pattern for this round of work.

## Resource — `sjvair/resources/tempo.py`

```python
class TempoResource(BaseResource):
    """NASA TEMPO satellite air-quality data (NO2, O3TOT, HCHO, CLDO4 —
    hourly gridded column-density measurements).

    Available on :attr:`SJVAirClient.tempo`.
    """

    PATH = 'tempo/'

    def products(self) -> list[dict[str, Any]]:
        """List TEMPO product metadata: label, units, and legend color stops.

        Excludes ``cldo4`` (QA-only, not a toggleable map layer) — it's still
        a valid ``product`` value for :meth:`granules`/:meth:`point`/:meth:`region`.
        """
        return self._client.get(self.PATH)['data']

    def granules(self, product: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate TEMPO granules for one product.

        Defaults to today's granules (America/Los_Angeles, falling back to
        yesterday if it's before noon and today's data isn't ready) when no
        ``date``/``timestamp`` filter is given. Filters: ``date``,
        ``timestamp``/``timestamp__lt``/``__lte``/``__gt``/``__gte``,
        ``is_final``, ``version``/``version__iexact``.
        """
        return self._paginate(f'{self.PATH}{product}/granules/', params or None)

    def latest_granule(self, product: str) -> dict[str, Any]:
        """Get the single most recent granule for one product."""
        return self._client.get(f'{self.PATH}{product}/granules/latest/')['data']

    def point(
        self,
        product: str,
        latitude: float,
        longitude: float,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        """Iterate an hourly point-value series for one product at a coordinate.

        ``start``/``end`` are ISO 8601 timestamps; omit both to default to
        today's available granules. Max range is 90 days.
        """
        params: dict[str, Any] = {'latitude': latitude, 'longitude': longitude}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        return self._client.get(f'{self.PATH}{product}/point/', params)['data']

    def region(
        self,
        product: str,
        region_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        """Iterate an hourly zonal-stats series for one product over a region boundary.

        Same ``start``/``end`` semantics as :meth:`point`.
        """
        params: dict[str, Any] = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
        return self._client.get(f'{self.PATH}{product}/region/{region_id}/', params or None)['data']
```

`products()`/`granules()`/`point()`/`region()` all send whatever `**params`
they build straight through — no enum/translation layer, matching every
other resource in this client.

## CLI — `sjvair tempo --type {products,granules,latest,point,region}`

One command, mirroring the existing `sjvair pesticides --type` precedent
(a resource with several differently-shaped sub-queries under one topical
command, rather than five separate commands):

```
sjvair tempo --type products
sjvair tempo --type granules --product no2 [--date YYYY-MM-DD] [--is-final] [--version V03]
sjvair tempo --type latest --product no2
sjvair tempo --type point --product no2 --lat 36.7468 --lon -119.7726 [--start ... --end ...]
sjvair tempo --type region --product no2 --county Fresno [--start ... --end ...]
```

- `--product` required for every type except `products`.
- `--type point` requires `--lat`/`--lon`.
- `--type region` requires exactly one region filter, reusing this CLI's
  existing `resolve_region()` helper (`--county`/`--city`/`--zip`/`--tract`/
  `--urban`/`--region-id`) — consistent with how CalEnviroScreen/CalHeatScore
  already resolve friendly region names to a region sqid.
- `products` and `latest` print indented JSON directly (`click.echo`), same
  precedent as `pesticides --type region-summary` — both are single-object-ish
  results, not tabular export candidates (`products`' nested `legend` array
  would flatten badly into CSV). `granules`, `point`, and `region` are
  genuinely row-per-record data, so they go through the normal
  `format_from_path`/`write_output` pipeline (`--output`/`--format` apply).

## Docs

New `docs/client/resources/tempo.md` and `docs/cli/data-export/tempo.md`,
added to both index pages and `docs/client/reference.md`'s autoclass list —
same wiring pattern as CalHeatScore.

## Testing

Same `responses`-mocked pattern as the rest of this client. Cover, at
minimum: `products()`, `granules()` (with and without filters), the
today-default behavior is server-side only (client sends no default date),
`latest_granule()`, `point()` (with/without start/end, latitude/longitude
sent correctly), `region()` (region_id in the URL path, start/end as query
params). CLI: all five `--type` values, plus the `--type point` missing
lat/lon error and `--type region` missing-region error.
