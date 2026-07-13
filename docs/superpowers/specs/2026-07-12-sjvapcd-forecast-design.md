# SJVAPCD daily forecast client support

## Context

A new dataset is landing on `sjvair/sjvair.com` (the backend) as an open,
unmerged PR (`feature/sjvapcd-forecast`, branch inspected directly in the
sibling checkout at `~/dev/ccac/sjvair.com`): SJVAPCD's daily air quality
forecast, ingested from their public XML feed and exposed at
`/api/2.0/forecasts/`.

Following the same precedent as CalEnviroScreen 5.0 and CalHeatScore (see
`2026-07-12-calenviroscreen5-calheatscore-design.md`), this client is built
against the PR's current diff rather than waiting for merge.

### API shape (from the backend PR)

- `GET /api/2.0/forecasts/` — list. Defaults to `forecast_date >= today`
  (current + future only) unless `forecast_date` is explicitly filtered.
  Filters: `region_id` (exact), `forecast_date` (`exact`/`lt`/`lte`/`gt`/`gte`),
  `issued_date` (same lookups).
- `GET /api/2.0/forecasts/<id>/` — single record, lookup by `sqid`.
- Fields: `id`, `region` (nested, full `RegionSerializer` incl. boundary),
  `zone_name`, `forecast_date`, `issued_date`, `published_at`, `aqi_value`,
  `aqi_category`, `pollutant` (`O3` or `PM2.5`), `burn_status`,
  `burn_status_text`, `air_alert`, `air_alert_start`, `air_alert_end`.
- One zone per SJV county (9 feed zones → 8 `Region` matches; one dropped,
  no client-side implication — the API simply won't return it).
- Every ingestion run writes two rows per zone: `forecast_date == issued_date`
  ("today") and `forecast_date == issued_date + 1` ("tomorrow"). Full history
  is kept — no upsert-to-latest.

## Client: new resource

`sjvair/resources/forecasts.py`, following the `hms.py` list+get shape
(simple collection, no sub-resources needed):

```python
class ForecastsResource(BaseResource):
    """SJVAPCD daily air quality forecasts. Available on :attr:`SJVAirClient.forecasts`."""

    PATH = 'forecasts/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate forecasts. Defaults to current + future (server-side) if no `forecast_date` filter is given."""
        return self._paginate(self.PATH, params or None)

    def get(self, forecast_id: str) -> dict[str, Any]:
        """Get a single forecast record by ID."""
        return self._client.get(f'{self.PATH}{forecast_id}/')['data']
```

Registered as `client.forecasts` in `sjvair/client.py`, alongside the other
resource imports/attributes.

## CLI: new flat command

`sjvair/cli/commands/forecasts.py`, following `calheatscore.py`'s flat
(non-group) shape plus `hms.py`'s region-flag handling via `resolve_region`:

```bash
sjvair forecasts                                  # current + future, all zones
sjvair forecasts --date 2026-07-13                # one forecast_date, all zones
sjvair forecasts --issued-date 2026-07-12         # one issued_date, all zones
sjvair forecasts --county Fresno                  # one zone, current + future
```

Flags: `--date` (maps to `forecast_date`), `--issued-date` (maps to
`issued_date`), the standard region flags (`--county`/`--city`/`--zip`/
`--tract`/`--urban`/`--region-id`) via `resolve_region`, plus the usual
`--output`/`--format`. Registered in `sjvair/cli/main.py` next to the other
flat commands (`calheatscore`, etc).

No `--horizon`/`--today`/`--tomorrow` flag — `forecast_date` already
distinguishes rows, and adding a second axis for the same distinction would
be redundant.

## Docs

- `docs/client/resources/forecasts.md` (new) — mirrors `calheatscore.md`'s
  structure: intro, example, methods table, filter list.
- `docs/client/resources/index.md` — add a Forecasts row/toctree entry.
- `docs/client/reference.md` — add `ForecastsResource` autoclass entry.
- `docs/cli/data-export/forecasts.md` (new) — mirrors `calheatscore.md`
  (CLI docs)/`hms.md`'s structure: command examples for each flag.
- `docs/cli/data-export/index.md` — add a row/toctree entry.
- `docs/index.md` — add an SJVAPCD Forecasts card under "Other Datasets"
  (it's a standalone dataset, not a `--device`-filterable monitor network,
  matching where CalHeatScore's forecast data already lives).
- `CHANGELOG.md` — `[Unreleased]` → `### Added`, matching the existing
  CalHeatScore/CalEnviroScreen5 entries' level of detail.

## Testing

Follow the existing `responses`-mocked pattern:

- `tests/test_resources/test_forecasts.py` — `list()` (default + with
  `forecast_date`/`issued_date`/`region_id` params), `get(forecast_id)`.
- `tests/test_cli/test_forecasts.py` — default invocation, `--date`,
  `--issued-date`, a region flag (`--county`), matching
  `test_cli/test_calheatscore.py`'s structure.

## Out of scope

- Backend ingestion/model/admin work — already built on the backend branch,
  not this repo's concern.
- Any handling for the dropped/unmapped feed zone (Sequoia National Park and
  Forest) — it's invisible to the API, so invisible to this client too.
