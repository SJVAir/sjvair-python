# Monitors Device-Filter Passthrough Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `MonitorsResource.closest()`, `.current()`, and `.current_at()` (and their CLI equivalents where they exist) pass a `device=` filter through to the backend, now that PR 253 on sjvair.com wires `?device=` into those three endpoints (previously silently ignored).

**Architecture:** Additive `**params` passthrough on the three resource methods, matching the existing convention already used by `list()`/`entries()` — no enum, no translation layer, whatever the caller passes goes straight into the query string. A `--device` option on the two CLI commands that already exist for these methods (`monitors closest`, `monitors current`; `current_at()` has no CLI command today and none is being added).

**Tech Stack:** Python 3.12, `click`, `requests`, `pytest` + `responses`, Sphinx + MyST.

## Global Constraints

- Design source of truth: `docs/superpowers/specs/2026-07-12-monitors-device-filter-design.md`.
- API base URL in tests: `https://www.sjvair.com/api/2.0/`.
- Fully backward compatible — no existing required argument changes. `**params` is purely additive.
- Do not document or wire `VOZBox` as a device value — it is not in the backend's device-name map yet (PR 250 gap, out of scope here).
- Confirmed device values to document: `PurpleAir`, `AirNow`, `AQview`, `BAM1022`, `AQLite`, `AirGradient`, `CIMIS`.
- Match existing code style: `from __future__ import annotations`, single quotes, `Any`/`Iterator` from `typing`.

---

### Task 1: Resource passthrough — `closest()`, `current()`, `current_at()`

**Files:**
- Modify: `sjvair/resources/monitors.py:116-145` (the three methods)
- Modify: `tests/test_resources/test_monitors.py:45-82` (existing closest/current/current_at tests)

**Interfaces:**
- Produces: `MonitorsResource.closest(entry_type, lat, lon, **params)`, `.current(entry_type, **params)`, `.current_at(entry_type, timestamp, region=None, bbox=None, **params)`. Consumed by Task 2 (CLI).

- [ ] **Step 1: Write the failing tests**

Add these three tests to `tests/test_resources/test_monitors.py` (place them immediately after the existing `test_monitors_closest`, `test_monitors_current`, and `test_monitors_current_at_with_region_and_bbox` tests respectively, so each new test sits next to the method it covers):

```python
@rsps.activate
def test_monitors_closest_with_device_filter():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/closest/', json={
        'data': [{'id': 'abc', 'distance': 100.0}], 'has_next_page': False
    })
    SJVAirClient().monitors.closest('pm25', 36.7468, -119.7726, device='CIMIS')
    assert 'device=CIMIS' in rsps.calls[0].request.url


@rsps.activate
def test_monitors_current_with_device_filter():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/current/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().monitors.current('pm25', device='AQLite'))
    assert 'device=AQLite' in rsps.calls[0].request.url


@rsps.activate
def test_monitors_current_at_with_device_filter():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/at/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().monitors.current_at('pm25', '2026-07-04T21:00:00', device='AirGradient'))
    assert 'device=AirGradient' in rsps.calls[0].request.url
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_resources/test_monitors.py -k device_filter -v`
Expected: FAIL — `TypeError: closest() got an unexpected keyword argument 'device'` (and similarly for `current`/`current_at`).

- [ ] **Step 3: Add `**params` passthrough to the three methods**

In `sjvair/resources/monitors.py`, replace:

```python
    def closest(self, entry_type: str, lat: float, lon: float) -> list[dict[str, Any]]:  # ty: ignore[invalid-type-form]
        """Return up to 3 nearest active monitors with distance and latest entry."""
        return self._client.get(f'monitors/{entry_type}/closest/', {'lat': lat, 'lon': lon})['data']

    def current(self, entry_type: str) -> Iterator[dict[str, Any]]:
        """Iterate all active monitors with their most recent entry for the given type."""
        return self._paginate(f'monitors/{entry_type}/current/')

    def current_at(
        self,
        entry_type: str,
        timestamp: str,
        region: list[str] | None = None,  # ty: ignore[invalid-type-form]
        bbox: tuple[float, float, float, float] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """As :meth:`current`, but as-of a historical ``timestamp`` (ISO 8601).

        Args:
            entry_type: Sensor field (e.g. ``'pm25'``).
            timestamp: ISO 8601 timestamp to query as-of.
            region: One or more region IDs to filter to monitors covered by their
                boundaries.
            bbox: ``(west, south, east, north)`` to filter to monitors within the box.
        """
        params: dict[str, Any] = {'timestamp': timestamp}
        if region:
            params['region'] = list(region)
        if bbox:
            params['bbox'] = ','.join(str(v) for v in bbox)
        return self._paginate(f'{self.PATH}{entry_type}/at/', params)
```

with:

```python
    def closest(
        self, entry_type: str, lat: float, lon: float, **params: Any
    ) -> list[dict[str, Any]]:  # ty: ignore[invalid-type-form]
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
        region: list[str] | None = None,  # ty: ignore[invalid-type-form]
        bbox: tuple[float, float, float, float] | None = None,
        **params: Any,
    ) -> Iterator[dict[str, Any]]:
        """As :meth:`current`, but as-of a historical ``timestamp`` (ISO 8601).

        Args:
            entry_type: Sensor field (e.g. ``'pm25'``).
            timestamp: ISO 8601 timestamp to query as-of.
            region: One or more region IDs to filter to monitors covered by their
                boundaries.
            bbox: ``(west, south, east, north)`` to filter to monitors within the box.

        Pass ``device`` to filter by device type (e.g. ``device='CIMIS'``).
        """
        params = {'timestamp': timestamp, **params}
        if region:
            params['region'] = list(region)
        if bbox:
            params['bbox'] = ','.join(str(v) for v in bbox)
        return self._paginate(f'{self.PATH}{entry_type}/at/', params)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_resources/test_monitors.py -v`
Expected: PASS (all monitors resource tests, including the 3 new ones and all pre-existing ones — confirms no regression to the no-`device` call shape).

- [ ] **Step 5: Commit**

```bash
git add sjvair/resources/monitors.py tests/test_resources/test_monitors.py
git commit -m "feat: pass device filter through closest/current/current_at"
```

---

### Task 2: CLI `--device` flag on `monitors closest` / `monitors current`

**Files:**
- Modify: `sjvair/cli/commands/monitors/closest.py` (full rewrite)
- Modify: `sjvair/cli/commands/monitors/current.py` (full rewrite)
- Create: `tests/test_cli/test_monitors_closest_current.py`

**Interfaces:**
- Consumes: `client.monitors.closest(entry_type, lat, lon, **params)`, `client.monitors.current(entry_type, **params)` (Task 1).
- Produces: `--device` option on `sjvair monitors closest`, `sjvair monitors current`. Consumed by Task 3 (docs).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli/test_monitors_closest_current.py`:

```python
from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_monitors_closest_device_flag():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/closest/', json={'data': [{'id': 'a'}], 'has_next_page': False})
    result = CliRunner().invoke(
        cli, ['monitors', 'closest', '--type', 'pm25', '--lat', '36.7468', '--lon', '-119.7726', '--device', 'CIMIS']
    )
    assert result.exit_code == 0, result.output
    assert 'device=CIMIS' in rsps.calls[0].request.url


@rsps.activate
def test_monitors_closest_without_device_flag():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/closest/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(
        cli, ['monitors', 'closest', '--type', 'pm25', '--lat', '36.7468', '--lon', '-119.7726']
    )
    assert result.exit_code == 0, result.output
    assert 'device' not in rsps.calls[0].request.url


@rsps.activate
def test_monitors_current_device_flag():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/current/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['monitors', 'current', '--type', 'pm25', '--device', 'AQLite'])
    assert result.exit_code == 0, result.output
    assert 'device=AQLite' in rsps.calls[0].request.url


@rsps.activate
def test_monitors_current_without_device_flag():
    rsps.add(rsps.GET, BASE + 'monitors/pm25/current/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['monitors', 'current', '--type', 'pm25'])
    assert result.exit_code == 0, result.output
    assert 'device' not in rsps.calls[0].request.url
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli/test_monitors_closest_current.py -v`
Expected: FAIL — `Error: No such option: --device`

- [ ] **Step 3: Rewrite `sjvair/cli/commands/monitors/closest.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

import click

from ...main import _ClientContext, pass_ctx


@click.command('closest')
@click.option('--type', 'entry_type', required=True)
@click.option('--lat', required=True, type=float)
@click.option('--lon', required=True, type=float)
@click.option('--device', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@pass_ctx
def monitors_closest(
    ctx: _ClientContext,
    entry_type: str,
    lat: float,
    lon: float,
    device: str | None,
    output_path: Path | None,
) -> None:
    """Up to 3 nearest active monitors with distance and latest entry."""
    params: dict[str, str] = {}
    if device:
        params['device'] = device
    data = ctx.client.monitors.closest(entry_type, lat, lon, **params)
    text = json.dumps(data, indent=2, default=str)
    if output_path:
        if output_path.exists() and not ctx.force:
            raise click.ClickException(f'{output_path} already exists. Use --force to overwrite.')
        output_path.write_text(text, encoding='utf-8')
    else:
        click.echo(text)
```

- [ ] **Step 4: Rewrite `sjvair/cli/commands/monitors/current.py`**

```python
from __future__ import annotations

from pathlib import Path

import click

from ...main import _ClientContext, pass_ctx
from ...utils import format_from_path, write_output


@click.command('current')
@click.option('--type', 'entry_type', required=True)
@click.option('--device', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def monitors_current(
    ctx: _ClientContext,
    entry_type: str,
    device: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """All active monitors with latest entry for the given type."""
    params: dict[str, str] = {}
    if device:
        params['device'] = device
    data = ctx.client.monitors.current(entry_type, **params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli/test_monitors_closest_current.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Run the full suite to confirm no regressions**

Run: `uv run pytest -m "not live" -q`
Expected: All tests pass, no regressions to any other `monitors` CLI test.

- [ ] **Step 7: Commit**

```bash
git add sjvair/cli/commands/monitors/closest.py sjvair/cli/commands/monitors/current.py tests/test_cli/test_monitors_closest_current.py
git commit -m "feat: add --device flag to monitors closest/current CLI commands"
```

---

### Task 3: Docs + CHANGELOG

**Files:**
- Modify: `docs/client/resources/monitors.md`
- Modify: `docs/cli/data-export/monitors.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `MonitorsResource.closest/current/current_at` (Task 1), `--device` CLI flags (Task 2). No code interfaces produced — docs-only, verified by a Sphinx build.

- [ ] **Step 1: Update `docs/client/resources/monitors.md`**

Replace the method-table rows for `closest`/`current`/`current_at` (currently):

```markdown
| `closest(entry_type, lat, lon)` | Up to 3 nearest active monitors with distance and latest entry. |
| `current(entry_type)` | All active monitors with their most recent entry. |
| `current_at(entry_type, timestamp, region=None, bbox=None)` | Like `current()`, but as of a historical timestamp. Optionally scope to one or more region IDs or a `(west, south, east, north)` bbox. |
```

with:

```markdown
| `closest(entry_type, lat, lon, **params)` | Up to 3 nearest active monitors with distance and latest entry. Pass `device` to filter by device type. |
| `current(entry_type, **params)` | All active monitors with their most recent entry. Pass `device` to filter by device type. |
| `current_at(entry_type, timestamp, region=None, bbox=None, **params)` | Like `current()`, but as of a historical timestamp. Optionally scope to one or more region IDs, a `(west, south, east, north)` bbox, or `device`. |
```

Then add a new section right after the `## Entries and summaries` section (at the end of the file):

```markdown
## Filtering by device

`list()`, `closest()`, `current()`, and `current_at()` all accept a `device` filter, matching one of the platform's monitor types:

```python
cimis_stations = list(client.monitors.current('temperature', device='CIMIS'))
```

Confirmed device values: `PurpleAir`, `AirNow`, `AQview`, `BAM1022`, `AQLite`, `AirGradient`, `CIMIS`. This list grows as new integrations land on the platform.

## Meteorological entry types

CIMIS weather stations report ten entry types beyond the usual pollutant fields, usable with `entries()`, `current()`, and `summaries()` like any other `entry_type`: `temperature`, `humidity`, `pressure`, `dewpoint`, `soiltemperature`, `windspeed`, `winddirection`, `precipitation`, `solarradiation`, `netradiation`, `vaporpressure`, `eto`, `etr`.
```

- [ ] **Step 2: Update `docs/cli/data-export/monitors.md`**

In the `## \`monitors current\`` section, add a `--device` example after the existing two:

```markdown
```bash
sjvair monitors current --type temperature --device CIMIS
```
```

In the `## \`monitors closest\`` section, add a `--device` example after the existing one:

```markdown
```bash
sjvair monitors closest --type pm25 --lat 36.7468 --lon -119.7726 --device AQLite
```
```

- [ ] **Step 3: Build the docs to verify they compile**

Run: `uv run sphinx-build -b html docs docs/_build/html`
Expected: Build succeeds, no new errors.

- [ ] **Step 4: Add CHANGELOG entry**

In `CHANGELOG.md`, under the existing `## [Unreleased]` / `### Added` section (added by the prior calenviroscreen5/calheatscore work), add:

```markdown
- **Client**: `client.monitors.closest()`, `.current()`, and `.current_at()`
  now accept `**params` (e.g. `device='CIMIS'`), matching `list()`'s existing
  filter passthrough — the backend now honors `?device=` on these endpoints.
- **CLI**: `--device` flag on `sjvair monitors closest` and
  `sjvair monitors current`.
```

If `### Added` doesn't already exist under `## [Unreleased]` (e.g. if this plan runs before the calenviroscreen5/calheatscore CHANGELOG entry), create it in the same position, following the file's existing Keep-a-Changelog structure.

- [ ] **Step 5: Commit**

```bash
git add docs/client/resources/monitors.md docs/cli/data-export/monitors.md CHANGELOG.md
git commit -m "docs: document device filter passthrough on monitors closest/current"
```

---

### Task 4: Final verification

**Files:** none (verification only)

**Interfaces:** Consumes everything from Tasks 1-3.

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -m "not live" -q`
Expected: All tests pass.

- [ ] **Step 2: Run the linter**

Run: `uv run ruff check sjvair/`
Expected: No new errors (any pre-existing unrelated errors in `sjvair/cli/commands/timelapse/` are out of scope for this plan).

- [ ] **Step 3: Run the type checker**

Run: `uv run ty check sjvair/resources/monitors.py sjvair/cli/commands/monitors/closest.py sjvair/cli/commands/monitors/current.py`
Expected: No errors.

- [ ] **Step 4: Smoke-test the CLI**

Run: `uv run sjvair monitors closest --help && uv run sjvair monitors current --help`
Expected: Both show a `--device` option in their usage text, no traceback.
