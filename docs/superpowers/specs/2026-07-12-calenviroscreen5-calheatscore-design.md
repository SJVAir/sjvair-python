# CalEnviroScreen 5.0 + CalHeatScore client support

## Context

Two new integrations are landing on `sjvair/sjvair.com` (the backend) as open PRs:

- **PR 247** — Adds CalEnviroScreen 5.0 (CES5) and restructures the existing CES4
  API: `year` moves from a URL path segment (`calenviroscreen/4.0/<year>/`) to an
  optional `?year=` query param (`calenviroscreen/4.0/?year=`, default `2020`).
  CES5 (`calenviroscreen/5.0/`) is a single-vintage dataset with no year concept
  at all, and has a different (larger) field set than CES4.
- **PR 254** — Adds a brand-new CalHeatScore dataset: daily ZIP-code-level heat
  risk scores (0–4) from CalEPA. `GET /calheatscore/` (all ZIPs, defaults to
  today, filterable by `date`/`date__gte`/`date__lte`, `score`/`score__gte`/
  `score__lte`, `zip_code`, `zip_code__in`) and `GET /calheatscore/<zip>/` (full
  history for one ZIP, filterable by the same `date`/`score` params).

Both PRs are open/unmerged upstream; we're building against their current diffs
now rather than waiting, and will true up the client if either shape shifts
before merge. Three other open PRs (AQLite, VOZbox, CIMIS) add new monitor
types that ride the existing generic `/monitors/` endpoint with no new API
surface — out of scope for this round. A fourth (TEMPO) has no REST API layer
yet at all. Neither needs client work yet.

## CalEnviroScreen: split into two resources, drop the bare name

CES4 and CES5 share a URL prefix but are otherwise unrelated: different field
sets, different filters, and only CES4 has a `year` concept. Rather than one
resource with a `version=` kwarg (which would need validation logic to reject
`year` when `version='5.0'`), they become two independent resource classes.

The existing bare `client.calenviroscreen` / `sjvair calenviroscreen` name is
retired rather than defaulting to either version — a future CES6 would raise
the same "what does the bare name mean" question again, so every version gets
an explicit, versioned name from the start.

### `sjvair/resources/calenviroscreen.py`

```python
class CalEnviroScreen4Resource(BaseResource):
    """CalEnviroScreen 4.0 census tract scores. Available on :attr:`SJVAirClient.calenviroscreen4`."""

    PATH = 'calenviroscreen/4.0/'

    def list(self, year: int | None = None, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate scored tracts. ``year`` defaults server-side to 2020 if omitted."""
        if year is not None:
            params['year'] = year
        return self._paginate(self.PATH, params or None)

    def get(self, tract: str, year: int | None = None) -> dict[str, Any]:
        """Get CalEnviroScreen 4.0 scores for a single census tract (FIPS code)."""
        params = {'year': year} if year is not None else None
        return self._client.get(f'{self.PATH}{tract}/', params)['data']


class CalEnviroScreen5Resource(BaseResource):
    """CalEnviroScreen 5.0 census tract scores. Available on :attr:`SJVAirClient.calenviroscreen5`."""

    PATH = 'calenviroscreen/5.0/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate scored tracts. No year filter — CES5 is single-vintage (2020 census tracts)."""
        return self._paginate(self.PATH, params or None)

    def get(self, tract: str) -> dict[str, Any]:
        """Get CalEnviroScreen 5.0 scores for a single census tract (FIPS code)."""
        return self._client.get(f'{self.PATH}{tract}/')['data']
```

Both keep the existing filter passthrough convention (`region_id`, `dac_sb535`,
`dac_category`, and `__gt`/`__gte`/`__lt`/`__lte` suffixes on score fields via
`**params`).

**Breaking changes** (acceptable pre-1.0, version is `0.1.0a3`):
- `client.calenviroscreen` → `client.calenviroscreen4` / `client.calenviroscreen5`.
- `CalEnviroScreen4Resource.get()` argument order changes from `get(year, tract)`
  to `get(tract, year=None)` — `year` becoming optional means it can't stay the
  first positional arg with no default while `tract` also has none.
- `list(year, ...)` on CES4 becomes `list(year=None, ...)` — existing positional
  calls (`list(2020, ...)`) keep working unchanged.

### CLI

`sjvair calenviroscreen` is replaced by two commands:

```bash
sjvair calenviroscreen4 --year 2010 --county Fresno
sjvair calenviroscreen4 --county Fresno              # year omitted, server defaults to 2020
sjvair calenviroscreen5 --tract 06019000100 --format yaml
```

`calenviroscreen4` keeps `--year` (now optional) plus the existing region
flags (`--county`/`--city`/`--zip`/`--tract`/`--urban`/`--region-id`).
`calenviroscreen5` drops `--year` entirely and keeps the region flags.

## CalHeatScore: new resource

### `sjvair/resources/calheatscore.py`

```python
class CalHeatScoreResource(BaseResource):
    """Daily ZIP-code-level heat-risk scores (0-4) from CalEPA's CalHeatScore.

    Available on :attr:`SJVAirClient.calheatscore`.
    """

    PATH = 'calheatscore/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate CalHeatScore rows across ZIP codes.

        Defaults to today (server-side) if no ``date`` filter is given. Filters:
        ``date``/``date__gte``/``date__lte``, ``score``/``score__gte``/``score__lte``,
        ``zip_code``, ``zip_code__in`` (comma-separated).
        """
        return self._paginate(self.PATH, params or None)

    def zip_code(self, zip_code: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate all stored CalHeatScore rows (history + forecast) for one ZIP code, newest first.

        Accepts the same ``date``/``score`` filters as :meth:`list` to narrow the range.
        """
        return self._paginate(f'{self.PATH}{zip_code}/', params or None)
```

`list()` and `zip_code()` return multiple rows in all cases (there's no
single-object "detail" shape for this dataset), so neither is named `get()` —
that name is reserved elsewhere in this client for single-dict lookups.

### CLI

```bash
sjvair calheatscore                              # today, all ZIPs
sjvair calheatscore --date 2026-07-13            # one date, all ZIPs
sjvair calheatscore --zip 93728                  # full history, one ZIP
sjvair calheatscore --zip 93728 --date 2026-07-13  # one ZIP, one date
```

Implementation: `--zip` alone or combined with `--date` calls
`client.calheatscore.zip_code(zip_code, date=...)`; `--date` alone or no flags
calls `client.calheatscore.list(date=...)`. No client-side filtering needed —
the server now handles the combined zip+date case directly.

## Docs & wiring

- `docs/client/resources/calenviroscreen.md` — rewritten to cover both
  `client.calenviroscreen4` and `client.calenviroscreen5` on one page (mirrors
  how `pesticides.md` covers multiple sub-resources on one page), with a note
  on the renamed/reshaped `get()`.
- `docs/client/resources/calheatscore.md` (new).
- `docs/client/resources/index.md` — update the CalEnviroScreen row/toctree
  entry, add a CalHeatScore row/toctree entry.
- `docs/cli/data-export/calenviroscreen.md` — rewritten for the two commands.
- `docs/cli/data-export/calheatscore.md` (new).
- `docs/cli/data-export/index.md` — update/add rows and toctree entries.
- `docs/client/reference.md` — replace the `CalEnviroScreenResource` autoclass
  entry with `CalEnviroScreen4Resource`/`CalEnviroScreen5Resource`; add
  `CalHeatScoreResource`.
- `sjvair/cli/main.py` — replace the `calenviroscreen` command registration
  with `calenviroscreen4`/`calenviroscreen5`; register the new `calheatscore`
  command.
- `sjvair/client.py` (`SJVAirClient`) — replace the `calenviroscreen` attribute
  with `calenviroscreen4`/`calenviroscreen5`; add `calheatscore`.
- `CHANGELOG.md` — `[Unreleased]` entries under `### Added` (CES5, CalHeatScore)
  and `### Changed` (the CES4 rename/breaking signature change), following the
  existing changelog's level of detail.

## Testing

Follow the existing `responses`-mocked pattern in `tests/test_resources/` and
`tests/test_cli/`:

- `tests/test_resources/test_calenviroscreen.py` — update existing CES4 tests
  for the new query-param URL shape and `client.calenviroscreen4`; add CES5
  tests for `client.calenviroscreen5`.
- `tests/test_resources/test_calheatscore.py` (new) — `list()` and `zip_code()`,
  including the combined zip+date case.
- `tests/test_cli/` — update/add CLI tests for `calenviroscreen4`,
  `calenviroscreen5`, and `calheatscore`, covering the flag combinations above.
