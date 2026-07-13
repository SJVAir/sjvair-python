# Monitor device-filter passthrough + new device/entry-type docs

## Context

Re-analysis of the three still-open "new monitor type" PRs on `sjvair/sjvair.com` (242 AQLite, 250 VOZbox, 253 CIMIS) turned up more than docs-only work:

- **PR 253 fixes a real backend bug**: `?device=` filtering was wired into `MonitorList` (`GET /monitors/`) but silently ignored on `ClosestMonitor` (`/monitors/{type}/closest/`), `CurrentData` (`/monitors/{type}/current/`), and `MonitorsAt` (`/monitors/{type}/at/`) — passing `?device=CIMIS` to those endpoints did nothing. PR 253 wires `MonitorFilter` into all three. This client's `MonitorsResource.closest()` and `.current()` currently accept **no extra params at all**, and `.current_at()` only accepts `region`/`bbox` — none can send `device=` today, so there's a real capability gap once this backend fix ships.
- Device-name → lookup-field values confirmed added server-side: `AQLite` (242), `AirGradient` + `CIMIS` (253). **`VOZBox` is not** — PR 250 never added it to the backend's hardcoded device-name map, so `?device=VOZBox` would silently no-op even after merge. This is a gap in PR 250 itself; out of scope for this client since there's nothing correct to wire against yet.
- PR 253 also adds 10 reusable meteorological entry types (`Temperature`, `Humidity`, `Pressure`, `DewPoint`, `SoilTemperature`, `WindSpeed`, `WindDirection`, `Precipitation`, `SolarRadiation`, `NetRadiation`, `VaporPressure`, `ETo`, `ETr`). These work today via the existing generic `entries()`/`current()`/`summaries()` methods (entry types are free-form strings, not an enum in this client) — just undocumented.

All three backend PRs remain open/unmerged; building against current diffs per the established pattern for this round of work.

## Resource changes — `sjvair/resources/monitors.py`

Add `**params` passthrough to the three methods that currently lack it, matching the existing convention already used by `list()`/`entries()` (query params forwarded as-is, no enum/translation layer):

```python
def closest(self, entry_type: str, lat: float, lon: float, **params: Any) -> list[dict[str, Any]]:
    """Return up to 3 nearest active monitors with distance and latest entry.

    Pass ``device`` to filter by device type (e.g. ``device='CIMIS'``).
    """
    return self._client.get(f'monitors/{entry_type}/closest/', {'lat': lat, 'lon': lon, **params})['data']

def current(self, entry_type: str, **params: Any) -> Iterator[dict[str, Any]]:
    """Iterate all active monitors with their most recent entry for the given type.

    Pass ``device`` to filter by device type (e.g. ``device='CIMIS'``).
    """
    return self._paginate(f'monitors/{entry_type}/current/', params or None)

def current_at(
    self,
    entry_type: str,
    timestamp: str,
    region: list[str] | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    **params: Any,
) -> Iterator[dict[str, Any]]:
    """As :meth:`current`, but as-of a historical ``timestamp`` (ISO 8601).

    Pass ``device`` to filter by device type. ``region``/``bbox`` unchanged.
    """
    params = {'timestamp': timestamp, **params}
    if region:
        params['region'] = list(region)
    if bbox:
        params['bbox'] = ','.join(str(v) for v in bbox)
    return self._paginate(f'{self.PATH}{entry_type}/at/', params)
```

No signature changes to existing required args — `**params` is purely additive, fully backward compatible (unlike the CalEnviroScreen work, no breaking change here).

## CLI changes

`sjvair monitors closest` and `sjvair monitors current` get a `--device` option (default `None`, only added to params when set). `current_at()` has no existing CLI command (pre-existing gap, unrelated to this work) — not adding one now, out of scope.

`sjvair/cli/commands/monitors/closest.py`:
```python
@click.option('--device', default=None)
...
def monitors_closest(ctx, entry_type, lat, lon, device, output_path):
    params = {}
    if device:
        params['device'] = device
    data = ctx.client.monitors.closest(entry_type, lat, lon, **params)
    ...
```

`sjvair/cli/commands/monitors/current.py`: same pattern.

## Docs

- `docs/client/resources/monitors.md`: update the `closest`/`current`/`current_at` method-table rows to show `**params`/`device=`; add a short note listing confirmed `device` values (`PurpleAir`, `AirNow`, `AQview`, `BAM1022`, `AQLite`, `AirGradient`, `CIMIS`) with a note that this list grows as new integrations land server-side (explicitly not documenting `VOZBox` — not wired yet). Add a short "Meteorological entry types" note listing the 10 new CIMIS entry types, since `entries()`/`current()`/`summaries()` already work with them once weather monitors exist.
- `docs/cli/data-export/monitors.md`: add `--device` examples to the `monitors closest`/`monitors current` sections.

## Testing

Same `responses`-mocked pattern as the rest of this client:
- `tests/test_resources/test_monitors.py`: assert `device=CIMIS` (or similar) appears in the request URL for `closest()`, `current()`, and `current_at()` when passed; assert existing calls without `device` are unaffected (no regression to current behavior/URLs).
- `tests/test_cli/test_monitors.py`: assert `--device` flag on `monitors closest`/`monitors current` propagates to the request URL; assert omitting it behaves as before.
