# CalEnviroScreen 5.0 + CalHeatScore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `client.calenviroscreen5` (new dataset) and `client.calheatscore` (new dataset) to the SJVAir Python client, split the existing `client.calenviroscreen` into version-explicit `calenviroscreen4`/`calenviroscreen5` resources, and expose all three via CLI commands and docs.

**Architecture:** Two new/changed resource classes in `sjvair/resources/`, wired onto `SJVAirClient` in `sjvair/client.py`; matching Click commands in `sjvair/cli/commands/`, wired into `sjvair/cli/main.py`; docs pages under `docs/client/resources/` and `docs/cli/data-export/`. Follows the existing patterns in this codebase exactly — see `sjvair/resources/pesticides.py` (sub-resource pattern reference) and `sjvair/resources/monitors.py` (single-resource pattern reference).

**Tech Stack:** Python 3.12, `click` (CLI), `requests` (HTTP), `pytest` + `responses` (HTTP-mocked tests), Sphinx + MyST (docs).

## Global Constraints

- Design source of truth: `docs/superpowers/specs/2026-07-12-calenviroscreen5-calheatscore-design.md`.
- API base URL in tests: `https://www.sjvair.com/api/2.0/` (constant `BASE` in existing test files).
- This is a breaking-change release (package is pre-1.0, currently `0.1.0a3`) — `client.calenviroscreen` and `sjvair calenviroscreen` are removed entirely, not deprecated/aliased.
- Every new/changed public method needs a one-or-two-sentence docstring (existing convention in `sjvair/resources/*.py`) since `docs/client/reference.md` autogenerates from them.
- Match existing code style: `from __future__ import annotations` at the top of every module, `Any`/`Iterator` from `typing`, single quotes.

---

### Task 1: CalEnviroScreen 4.0 / 5.0 resources

**Files:**
- Modify: `sjvair/resources/calenviroscreen.py` (full rewrite)
- Modify: `sjvair/client.py:40-41` (docstring), `:76`, `:80`, `:85` (imports/wiring)
- Modify: `tests/test_resources/test_calenviroscreen.py` (full rewrite)

**Interfaces:**
- Produces: `CalEnviroScreen4Resource.list(year: int | None = None, **params) -> Iterator[dict]`, `CalEnviroScreen4Resource.get(tract: str, year: int | None = None) -> dict`, `CalEnviroScreen5Resource.list(**params) -> Iterator[dict]`, `CalEnviroScreen5Resource.get(tract: str) -> dict`, `SJVAirClient.calenviroscreen4`, `SJVAirClient.calenviroscreen5`. Consumed by Task 2 (CLI) and Task 5 (docs).

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `tests/test_resources/test_calenviroscreen.py`:

```python
from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_ces4_list() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [{'tract': '06019000100'}], 'has_next_page': False})
    assert list(SJVAirClient().calenviroscreen4.list(2021))[0]['tract'] == '06019000100'


@rsps.activate
def test_ces4_list_sends_year_query_param() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().calenviroscreen4.list(2021))
    assert 'year=2021' in rsps.calls[0].request.url


@rsps.activate
def test_ces4_list_omits_year_query_param_when_not_given() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().calenviroscreen4.list())
    assert 'year' not in rsps.calls[0].request.url


@rsps.activate
def test_ces4_get() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/06019000100/', json={'data': {'score': 85.2}})
    assert SJVAirClient().calenviroscreen4.get('06019000100', year=2021)['score'] == 85.2


@rsps.activate
def test_ces4_get_omits_year_query_param_when_not_given() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/06019000100/', json={'data': {'score': 85.2}})
    SJVAirClient().calenviroscreen4.get('06019000100')
    assert 'year' not in rsps.calls[0].request.url


@rsps.activate
def test_ces5_list() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/5.0/', json={'data': [{'tract': '06019000100'}], 'has_next_page': False})
    assert list(SJVAirClient().calenviroscreen5.list())[0]['tract'] == '06019000100'


@rsps.activate
def test_ces5_get() -> None:
    rsps.add(rsps.GET, BASE + 'calenviroscreen/5.0/06019000100/', json={'data': {'score': 91.0}})
    assert SJVAirClient().calenviroscreen5.get('06019000100')['score'] == 91.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_resources/test_calenviroscreen.py -v`
Expected: FAIL — `AttributeError: 'SJVAirClient' object has no attribute 'calenviroscreen4'` (old `calenviroscreen` attribute still exists at this point).

- [ ] **Step 3: Rewrite the resource module**

Replace the full contents of `sjvair/resources/calenviroscreen.py`:

```python
from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class CalEnviroScreen4Resource(BaseResource):
    """Access CalEnviroScreen 4.0 census tract cumulative impact scores.

    Available on :attr:`SJVAirClient.calenviroscreen4`.
    """

    PATH = 'calenviroscreen/4.0/'

    def list(self, year: int | None = None, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate census tract scores.

        ``year`` defaults server-side to 2020 if omitted. Filters are applied
        server-side. Pass ``region_id`` to scope to a region, ``dac_sb535``/
        ``dac_category`` for the disadvantaged-community designation, or
        ``__gt``/``__gte``/``__lt``/``__lte`` suffixes for threshold lookups on
        any score field (e.g. ``pollution_p__gte=75``).
        """
        if year is not None:
            params['year'] = year
        return self._paginate(self.PATH, params or None)

    def get(self, tract: str, year: int | None = None) -> dict[str, Any]:
        """Get CalEnviroScreen 4.0 scores for a single census tract (FIPS code).

        ``year`` defaults server-side to 2020 if omitted.
        """
        params = {'year': year} if year is not None else None
        return self._client.get(f'{self.PATH}{tract}/', params)['data']


class CalEnviroScreen5Resource(BaseResource):
    """Access CalEnviroScreen 5.0 census tract cumulative impact scores.

    Available on :attr:`SJVAirClient.calenviroscreen5`.
    """

    PATH = 'calenviroscreen/5.0/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate census tract scores.

        Single-vintage dataset (2020 census tracts) — no ``year`` filter.
        Filters are applied server-side. Pass ``region_id`` to scope to a
        region, ``dac_sb535``/``dac_category`` for the disadvantaged-community
        designation, or ``__gt``/``__gte``/``__lt``/``__lte`` suffixes for
        threshold lookups on any score field.
        """
        return self._paginate(self.PATH, params or None)

    def get(self, tract: str) -> dict[str, Any]:
        """Get CalEnviroScreen 5.0 scores for a single census tract (FIPS code)."""
        return self._client.get(f'{self.PATH}{tract}/')['data']
```

- [ ] **Step 4: Wire the new resources into `SJVAirClient`**

In `sjvair/client.py`, update the class docstring (lines 40-41):

```python
    All resource objects (``monitors``, ``regions``, ``calenviroscreen4``,
    ``calenviroscreen5``, ``ceidars``, ``hms``, ``pesticides``) are attached as
    attributes and share this client's session,
```

Then replace the import and wiring block (originally lines 76-88):

```python
        from .resources.calenviroscreen import CalEnviroScreen4Resource, CalEnviroScreen5Resource
        from .resources.ceidars import CEIDARSResource
        from .resources.hms import HMSResource
        from .resources.monitors import MonitorsResource
        from .resources.pesticides import PesticidesResource
        from .resources.regions import RegionsResource

        self.monitors = MonitorsResource(self)
        self.regions = RegionsResource(self)
        self.calenviroscreen4 = CalEnviroScreen4Resource(self)
        self.calenviroscreen5 = CalEnviroScreen5Resource(self)
        self.ceidars = CEIDARSResource(self)
        self.hms = HMSResource(self)
        self.pesticides = PesticidesResource(self)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_resources/test_calenviroscreen.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
git add sjvair/resources/calenviroscreen.py sjvair/client.py tests/test_resources/test_calenviroscreen.py
git commit -m "feat: split calenviroscreen into calenviroscreen4/calenviroscreen5 resources"
```

---

### Task 2: CalEnviroScreen 4.0 / 5.0 CLI commands

**Files:**
- Modify: `sjvair/cli/commands/calenviroscreen.py` (full rewrite)
- Modify: `sjvair/cli/main.py:79-97` (imports/registration)
- Create: `tests/test_cli/test_calenviroscreen.py`

**Interfaces:**
- Consumes: `client.calenviroscreen4.list(year, **params)`, `client.calenviroscreen5.list(**params)` (Task 1).
- Produces: `sjvair calenviroscreen4`, `sjvair calenviroscreen5` Click commands. Consumed by Task 6 (docs).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli/test_calenviroscreen.py`:

```python
from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_calenviroscreen4_list():
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [{'tract': '06019000100'}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calenviroscreen4', '--year', '2020'])
    assert result.exit_code == 0, result.output
    assert '06019000100' in result.output
    assert 'year=2020' in rsps.calls[0].request.url


@rsps.activate
def test_calenviroscreen4_year_is_optional():
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calenviroscreen4'])
    assert result.exit_code == 0, result.output
    assert 'year' not in rsps.calls[0].request.url


@rsps.activate
def test_calenviroscreen4_region_filter():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r1', 'name': 'Fresno County', 'type': 'county'}]})
    rsps.add(rsps.GET, BASE + 'calenviroscreen/4.0/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calenviroscreen4', '--county', 'Fresno'])
    assert result.exit_code == 0, result.output
    assert 'region_id=r1' in rsps.calls[-1].request.url


@rsps.activate
def test_calenviroscreen5_list():
    rsps.add(rsps.GET, BASE + 'calenviroscreen/5.0/', json={'data': [{'tract': '06019000100'}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calenviroscreen5'])
    assert result.exit_code == 0, result.output
    assert '06019000100' in result.output


def test_calenviroscreen5_has_no_year_flag():
    result = CliRunner().invoke(cli, ['calenviroscreen5', '--year', '2020'])
    assert result.exit_code != 0
    assert 'no such option' in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli/test_calenviroscreen.py -v`
Expected: FAIL — `Error: No such command 'calenviroscreen4'.`

- [ ] **Step 3: Rewrite the CLI command module**

Replace the full contents of `sjvair/cli/commands/calenviroscreen.py`:

```python
from __future__ import annotations

from pathlib import Path

import click

from ..main import _ClientContext, pass_ctx
from ..utils import format_from_path, resolve_region, write_output


@click.command('calenviroscreen4')
@click.option('--year', default=None, type=int)
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--urban', default=None)
@click.option('--region-id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def calenviroscreen4(
    ctx: _ClientContext,
    year: int | None,
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    urban: str | None,
    region_id: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """CalEnviroScreen 4.0 census tract scores."""
    params: dict[str, str] = {}
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id, urban)
    if region:
        params['region_id'] = region
    data = ctx.client.calenviroscreen4.list(year, **params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)


@click.command('calenviroscreen5')
@click.option('--county', default=None)
@click.option('--city', default=None)
@click.option('--zip', 'zip_code', default=None)
@click.option('--tract', default=None)
@click.option('--urban', default=None)
@click.option('--region-id', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def calenviroscreen5(
    ctx: _ClientContext,
    county: str | None,
    city: str | None,
    zip_code: str | None,
    tract: str | None,
    urban: str | None,
    region_id: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """CalEnviroScreen 5.0 census tract scores."""
    params: dict[str, str] = {}
    region = resolve_region(ctx.client, county, city, zip_code, tract, region_id, urban)
    if region:
        params['region_id'] = region
    data = ctx.client.calenviroscreen5.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

- [ ] **Step 4: Register both commands in `sjvair/cli/main.py`**

Replace the import block (originally lines 79-84):

```python
from .commands import (  # noqa: E402
    calenviroscreen,
    ceidars,
    hms,
    pesticides,
)
```

(unchanged — `calenviroscreen` module import already covers both new commands). Replace the registration line (originally line 94):

```python
cli.add_command(calenviroscreen.calenviroscreen4)
cli.add_command(calenviroscreen.calenviroscreen5)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli/test_calenviroscreen.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add sjvair/cli/commands/calenviroscreen.py sjvair/cli/main.py tests/test_cli/test_calenviroscreen.py
git commit -m "feat: add calenviroscreen4/calenviroscreen5 CLI commands"
```

---

### Task 3: CalHeatScore resource

**Files:**
- Create: `sjvair/resources/calheatscore.py`
- Modify: `sjvair/client.py` (docstring, imports, wiring)
- Create: `tests/test_resources/test_calheatscore.py`

**Interfaces:**
- Produces: `CalHeatScoreResource.list(**params) -> Iterator[dict]`, `CalHeatScoreResource.zipcode(zipcode: str, **params) -> Iterator[dict]`, `SJVAirClient.calheatscore`. Consumed by Task 4 (CLI) and Task 5 (docs).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_resources/test_calheatscore.py`:

```python
from __future__ import annotations

import responses as rsps
from sjvair.client import SJVAirClient

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_calheatscore_list() -> None:
    rsps.add(rsps.GET, BASE + 'calheatscore/', json={'data': [{'zipcode': '93728', 'score': 3}], 'has_next_page': False})
    assert list(SJVAirClient().calheatscore.list())[0]['zipcode'] == '93728'


@rsps.activate
def test_calheatscore_list_sends_date_query_param() -> None:
    rsps.add(rsps.GET, BASE + 'calheatscore/', json={'data': [], 'has_next_page': False})
    list(SJVAirClient().calheatscore.list(date='2026-07-13'))
    assert 'date=2026-07-13' in rsps.calls[0].request.url


@rsps.activate
def test_calheatscore_zipcode() -> None:
    rsps.add(rsps.GET, BASE + 'calheatscore/93728/', json={'data': [{'date': '2026-07-12', 'score': 3}], 'has_next_page': False})
    rows = list(SJVAirClient().calheatscore.zipcode('93728'))
    assert rows[0]['date'] == '2026-07-12'


@rsps.activate
def test_calheatscore_zipcode_with_date_filter() -> None:
    rsps.add(rsps.GET, BASE + 'calheatscore/93728/', json={'data': [{'date': '2026-07-13', 'score': 1}], 'has_next_page': False})
    list(SJVAirClient().calheatscore.zipcode('93728', date='2026-07-13'))
    assert 'date=2026-07-13' in rsps.calls[0].request.url
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_resources/test_calheatscore.py -v`
Expected: FAIL — `AttributeError: 'SJVAirClient' object has no attribute 'calheatscore'`

- [ ] **Step 3: Write the resource module**

Create `sjvair/resources/calheatscore.py`:

```python
from __future__ import annotations

from typing import Any, Iterator

from . import BaseResource


class CalHeatScoreResource(BaseResource):
    """Daily ZIP-code-level heat-risk scores (0-4) from CalEPA's CalHeatScore.

    Available on :attr:`SJVAirClient.calheatscore`.
    """

    PATH = 'calheatscore/'

    def list(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate CalHeatScore rows across ZIP codes.

        Defaults to today (server-side) if no ``date`` filter is given.
        Filters: ``date``/``date__gte``/``date__lte``,
        ``score``/``score__gte``/``score__lte``, ``zipcode``,
        ``zipcode__in`` (comma-separated).
        """
        return self._paginate(self.PATH, params or None)

    def zipcode(self, zipcode: str, **params: Any) -> Iterator[dict[str, Any]]:
        """Iterate all stored CalHeatScore rows (history + forecast) for one ZIP code, newest first.

        Accepts the same ``date``/``score`` filters as :meth:`list` to narrow the range.
        """
        return self._paginate(f'{self.PATH}{zipcode}/', params or None)
```

- [ ] **Step 4: Wire the resource into `SJVAirClient`**

In `sjvair/client.py`, update the class docstring (the line set by Task 1, Step 4):

```python
    All resource objects (``monitors``, ``regions``, ``calenviroscreen4``,
    ``calenviroscreen5``, ``ceidars``, ``hms``, ``pesticides``,
    ``calheatscore``) are attached as attributes and share this client's
    session,
```

Add the import alongside the others set by Task 1:

```python
        from .resources.calheatscore import CalHeatScoreResource
```

Add the attribute assignment after `self.pesticides = PesticidesResource(self)`:

```python
        self.pesticides = PesticidesResource(self)
        self.calheatscore = CalHeatScoreResource(self)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_resources/test_calheatscore.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add sjvair/resources/calheatscore.py sjvair/client.py tests/test_resources/test_calheatscore.py
git commit -m "feat: add calheatscore resource"
```

---

### Task 4: CalHeatScore CLI command

**Files:**
- Create: `sjvair/cli/commands/calheatscore.py`
- Modify: `sjvair/cli/main.py` (import/registration)
- Create: `tests/test_cli/test_calheatscore.py`

**Interfaces:**
- Consumes: `client.calheatscore.list(**params)`, `client.calheatscore.zipcode(zipcode, **params)` (Task 3).
- Produces: `sjvair calheatscore` Click command. Consumed by Task 6 (docs).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli/test_calheatscore.py`:

```python
from __future__ import annotations

import responses as rsps
from click.testing import CliRunner
from sjvair.cli.main import cli

BASE = 'https://www.sjvair.com/api/2.0/'


@rsps.activate
def test_calheatscore_defaults_to_list():
    rsps.add(rsps.GET, BASE + 'calheatscore/', json={'data': [{'zipcode': '93728', 'score': 3}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calheatscore'])
    assert result.exit_code == 0, result.output
    assert '93728' in result.output


@rsps.activate
def test_calheatscore_date_flag():
    rsps.add(rsps.GET, BASE + 'calheatscore/', json={'data': [], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calheatscore', '--date', '2026-07-13'])
    assert result.exit_code == 0, result.output
    assert 'date=2026-07-13' in rsps.calls[0].request.url


@rsps.activate
def test_calheatscore_zip_flag_hits_by_zip_endpoint():
    rsps.add(rsps.GET, BASE + 'calheatscore/93728/', json={'data': [{'date': '2026-07-12', 'score': 3}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calheatscore', '--zip', '93728'])
    assert result.exit_code == 0, result.output
    assert '2026-07-12' in result.output


@rsps.activate
def test_calheatscore_zip_and_date_combined():
    rsps.add(rsps.GET, BASE + 'calheatscore/93728/', json={'data': [{'date': '2026-07-13', 'score': 1}], 'has_next_page': False})
    result = CliRunner().invoke(cli, ['calheatscore', '--zip', '93728', '--date', '2026-07-13'])
    assert result.exit_code == 0, result.output
    assert 'date=2026-07-13' in rsps.calls[0].request.url
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli/test_calheatscore.py -v`
Expected: FAIL — `Error: No such command 'calheatscore'.`

- [ ] **Step 3: Write the CLI command module**

Create `sjvair/cli/commands/calheatscore.py`:

```python
from __future__ import annotations

from pathlib import Path

import click

from ..main import _ClientContext, pass_ctx
from ..utils import format_from_path, write_output


@click.command('calheatscore')
@click.option('--zip', 'zipcode', default=None)
@click.option('--date', default=None)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def calheatscore(
    ctx: _ClientContext,
    zipcode: str | None,
    date: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """CalEPA CalHeatScore daily ZIP-code heat-risk scores."""
    params: dict[str, str] = {}
    if date:
        params['date'] = date
    if zipcode:
        data = ctx.client.calheatscore.zipcode(zipcode, **params)
    else:
        data = ctx.client.calheatscore.list(**params)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

- [ ] **Step 4: Register the command in `sjvair/cli/main.py`**

Add `calheatscore` to the existing import block from `.commands`:

```python
from .commands import (  # noqa: E402
    calenviroscreen,
    calheatscore,
    ceidars,
    hms,
    pesticides,
)
```

Add the registration line after the pesticides registration:

```python
cli.add_command(pesticides.pesticides)
cli.add_command(calheatscore.calheatscore)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli/test_calheatscore.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add sjvair/cli/commands/calheatscore.py sjvair/cli/main.py tests/test_cli/test_calheatscore.py
git commit -m "feat: add calheatscore CLI command"
```

---

### Task 5: Client (Python) docs

**Files:**
- Modify: `docs/client/resources/calenviroscreen.md` (full rewrite)
- Create: `docs/client/resources/calheatscore.md`
- Modify: `docs/client/resources/index.md`
- Modify: `docs/client/reference.md`

**Interfaces:**
- Consumes: `CalEnviroScreen4Resource`/`CalEnviroScreen5Resource` (Task 1), `CalHeatScoreResource` (Task 3). No code interfaces produced — this task is docs-only, verified by a Sphinx build.

- [ ] **Step 1: Rewrite `docs/client/resources/calenviroscreen.md`**

```markdown
# CalEnviroScreen — `client.calenviroscreen4` / `client.calenviroscreen5`

CalEnviroScreen cumulative impact scores by census tract — pollution burden, population characteristics, and the overall CI score, plus the disadvantaged-community (SB 535) designation. Two versions are exposed as separate resources; there's no bare/default `client.calenviroscreen`, so a future CalEnviroScreen 6.0 doesn't have to fight over what the short name means.

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    tract4 = client.calenviroscreen4.get('06019000100', year=2020)
    tract5 = client.calenviroscreen5.get('06019000100')
```

## CalEnviroScreen 4.0 — `client.calenviroscreen4`

| Method | Signature |
|---|---|
| `list(year=None, **params)` | Iterate scored tracts. `year` defaults server-side to 2020 if omitted. |
| `get(tract, year=None)` | A single tract's full indicator set. |

```python
{
    "tract": "06019000100",
    "census_year": 2020,
    "population": 3842,
    "ci_score": 62.4,
    "ci_score_p": 84.0,
    "dac_sb535": True,
    "pollution": 71.2,
    "pol_ozone": 0.058,
    "pol_pm": 12.9,
    "pol_diesel": 38.4,
    "popchar": 55.6,
    "char_asthma": 84.3,
    "char_pov": 41.2,
    "pop_hispanic": 2891,
    # ...plus every other CalEnviroScreen indicator (pol_*, char_*, pop_*)
}
```

Filters happen server-side, not client-side — pass `region_id` to scope to a region, and `__gt`/`__gte`/`__lt`/`__lte` suffixes for threshold lookups on any score field:

```python
# Every tract in Fresno County in the top quartile for pollution burden
tracts = list(client.calenviroscreen4.list(
    year=2020,
    region_id='r6phe',
    pollution_p__gte=75,
))
```

Other useful filters: `dac_sb535` (boolean — SB 535 disadvantaged-community designation), `dac_category`, and `__gt`/`__gte`/`__lt`/`__lte` on `ci_score`, `ci_score_p`, `popchar_p`, `pol_pm_p`, `pol_ozone_p`, `pol_diesel_p`, and `pol_traffic_p`.

## CalEnviroScreen 5.0 — `client.calenviroscreen5`

| Method | Signature |
|---|---|
| `list(**params)` | Iterate scored tracts. Single-vintage dataset (2020 census tracts) — no `year` filter. |
| `get(tract)` | A single tract's full indicator set. |

CES5 adds `zipcode`, `approx_loc`, `county`, and `region_name` fields, plus a wider set of pollution/population-characteristic sub-indicators than CES4:

```python
# Every tract in Fresno County above the median for the small agricultural-tox-sites indicator
tracts = list(client.calenviroscreen5.list(
    region_id='r6phe',
    pol_small_ats_p__gte=50,
))
```

Same filter conventions as CES4: `region_id`, `dac_sb535`, `dac_category`, and `__gt`/`__gte`/`__lt`/`__lte` on any score field.
```

- [ ] **Step 2: Create `docs/client/resources/calheatscore.md`**

```markdown
# CalHeatScore — `client.calheatscore`

Daily ZIP-code-level heat-risk scores (0–4) from CalEPA's [CalHeatScore](https://calheatscore.calepa.ca.gov/), covering San Joaquin Valley ZIP codes. Includes a 7-day rolling forecast alongside recent actuals.

```python
from sjvair import SJVAirClient

with SJVAirClient() as client:
    today = list(client.calheatscore.list())
    print(today[0])
```

```python
{
    "zipcode": "93728",
    "date": "2026-07-12",
    "score": 3,
    "score_display": "High",
}
```

## Methods

| Method | Signature |
|---|---|
| `list(**params)` | Iterate scores across ZIP codes. Defaults to today (server-side) if no `date` filter is given. |
| `zipcode(zipcode, **params)` | Iterate all stored scores (history + forecast) for one ZIP code, newest first. |

Both accept the same server-side filters: `date`/`date__gte`/`date__lte`, `score`/`score__gte`/`score__lte`. `list()` additionally accepts `zipcode`/`zipcode__in` (comma-separated) to scope to specific ZIPs without using `zipcode()`.

```python
# One ZIP's score on a specific date
scores = list(client.calheatscore.zipcode('93728', date='2026-07-13'))

# Every ZIP scoring "High" or worse today
high_risk = list(client.calheatscore.list(score__gte=3))
```
```

- [ ] **Step 3: Update `docs/client/resources/index.md`**

Replace the full contents:

```markdown
# Resources

Each resource on `SJVAirClient` wraps one part of the SJVAir API.

| Resource | Attribute |
|---|---|
| [Air Monitors](monitors.md) | `client.monitors` |
| [Regions](regions.md) | `client.regions` |
| [CalEnviroScreen](calenviroscreen.md) | `client.calenviroscreen4` / `client.calenviroscreen5` |
| [CalHeatScore](calheatscore.md) | `client.calheatscore` |
| [Facility Emissions](ceidars.md) | `client.ceidars` |
| [Fire & Smoke](hms.md) | `client.hms` |
| [Pesticides](pesticides.md) | `client.pesticides` |

```{toctree}
:hidden:

Air Monitors <monitors>
Regions <regions>
CalEnviroScreen <calenviroscreen>
CalHeatScore <calheatscore>
Facility Emissions <ceidars>
Fire & Smoke <hms>
Pesticides <pesticides>
```
```

- [ ] **Step 4: Update `docs/client/reference.md`**

Replace:

```
.. autoclass:: sjvair.resources.calenviroscreen.CalEnviroScreenResource
   :members:
```

with:

```
.. autoclass:: sjvair.resources.calenviroscreen.CalEnviroScreen4Resource
   :members:

.. autoclass:: sjvair.resources.calenviroscreen.CalEnviroScreen5Resource
   :members:
```

And replace:

```
.. autoclass:: sjvair.resources.pesticides.PesticidesResource
   :members:
```

with:

```
.. autoclass:: sjvair.resources.pesticides.PesticidesResource
   :members:

.. autoclass:: sjvair.resources.calheatscore.CalHeatScoreResource
   :members:
```

- [ ] **Step 5: Build the docs to verify they compile**

Run: `uv sync --group docs && uv run sphinx-build -b html docs docs/_build/html`
Expected: Build succeeds (`build succeeded` or with only pre-existing warnings — no new errors referencing `calenviroscreen`, `calheatscore`, or the removed `CalEnviroScreenResource`/`client.calenviroscreen`).

- [ ] **Step 6: Commit**

```bash
git add docs/client/resources/calenviroscreen.md docs/client/resources/calheatscore.md docs/client/resources/index.md docs/client/reference.md
git commit -m "docs: document calenviroscreen4/5 and calheatscore client resources"
```

---

### Task 6: CLI docs

**Files:**
- Modify: `docs/cli/data-export/calenviroscreen.md` (full rewrite)
- Create: `docs/cli/data-export/calheatscore.md`
- Modify: `docs/cli/data-export/index.md`

**Interfaces:**
- Consumes: `sjvair calenviroscreen4`/`sjvair calenviroscreen5` (Task 2), `sjvair calheatscore` (Task 4). No code interfaces produced — docs-only, verified by a Sphinx build.

- [ ] **Step 1: Rewrite `docs/cli/data-export/calenviroscreen.md`**

```markdown
# CalEnviroScreen

CalEnviroScreen cumulative-impact scores by census tract. Two versions, as separate commands — there's no bare `calenviroscreen` command, so a future CalEnviroScreen 6.0 doesn't have to fight over what the short name means.

## `calenviroscreen4`

CalEnviroScreen 4.0, keyed to a `--year` (the census year the scores are based on — omit it and the server defaults to 2020).

Scope to a single region with `--county`, `--city`, `--zip`, `--tract` (FIPS), `--urban`, or `--region-id` — at most one. Omit the region filter to export every scored tract in the state.

```bash
sjvair calenviroscreen4 --year 2020
```

```bash
sjvair calenviroscreen4 --year 2020 --county Fresno --output ces4-fresno.csv
```

```bash
sjvair calenviroscreen4 --tract 06019000100 --format yaml
```

## `calenviroscreen5`

CalEnviroScreen 5.0 — single-vintage (2020 census tracts), so there's no `--year` flag. Same region flags as `calenviroscreen4`.

```bash
sjvair calenviroscreen5 --county Fresno --output ces5-fresno.csv
```

```bash
sjvair calenviroscreen5 --tract 06019000100 --format yaml
```
```

- [ ] **Step 2: Create `docs/cli/data-export/calheatscore.md`**

```markdown
# CalHeatScore

Daily ZIP-code-level heat-risk scores (0–4) from CalEPA's CalHeatScore, covering San Joaquin Valley ZIP codes.

## `calheatscore`

No flags returns today's score for every SJV ZIP code. `--date` scopes to a specific date; `--zip` scopes to a specific ZIP's full history (past actuals + forecast); combine both for one ZIP on one date.

```bash
sjvair calheatscore
```

```bash
sjvair calheatscore --date 2026-07-13
```

```bash
sjvair calheatscore --zip 93728
```

```bash
sjvair calheatscore --zip 93728 --date 2026-07-13
```
```

- [ ] **Step 3: Update `docs/cli/data-export/index.md`**

Replace the full contents:

```markdown
# Data export

Commands for listing, filtering, and bulk-exporting the datasets SJVAir aggregates.

| Page | Command |
|---|---|
| [Air Monitors](monitors.md) | `sjvair monitors` |
| [Regions](regions.md) | `sjvair regions` |
| [CalEnviroScreen](calenviroscreen.md) | `sjvair calenviroscreen4` / `sjvair calenviroscreen5` |
| [CalHeatScore](calheatscore.md) | `sjvair calheatscore` |
| [Facility Emissions](ceidars.md) | `sjvair ceidars` |
| [Fire & Smoke](hms.md) | `sjvair hms` |
| [Pesticides](pesticides.md) | `sjvair pesticides` |

```{toctree}
:hidden:

monitors
regions
calenviroscreen
calheatscore
ceidars
hms
pesticides
```
```

- [ ] **Step 4: Build the docs to verify they compile**

Run: `uv run sphinx-build -b html docs docs/_build/html`
Expected: Build succeeds, no new errors.

- [ ] **Step 5: Commit**

```bash
git add docs/cli/data-export/calenviroscreen.md docs/cli/data-export/calheatscore.md docs/cli/data-export/index.md
git commit -m "docs: document calenviroscreen4/5 and calheatscore CLI commands"
```

---

### Task 7: CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: nothing (documents the completed work from Tasks 1-6).

- [ ] **Step 1: Add entries under `## [Unreleased]`**

Replace:

```markdown
## [Unreleased]
```

with:

```markdown
## [Unreleased]

### Added

- **Client**: `client.calenviroscreen5` — CalEnviroScreen 5.0 census tract
  scores (`list(**params)`, `get(tract)`). Single-vintage dataset, no `year`
  filter.
- **CLI**: `sjvair calenviroscreen5` — CalEnviroScreen 5.0 export.
- **Client**: `client.calheatscore` — CalEPA CalHeatScore daily ZIP-code
  heat-risk scores (`list(**params)`, `zipcode(zipcode, **params)`).
- **CLI**: `sjvair calheatscore` — CalHeatScore export, with `--zip` and
  `--date` flags.

### Changed

- **Breaking**: `client.calenviroscreen` is replaced by
  `client.calenviroscreen4` (CES4) and `client.calenviroscreen5` (CES5) —
  there's no bare/default version, so a future CES6 doesn't have to fight
  over what the short name means. `CalEnviroScreen4Resource.get()`'s argument
  order changes from `get(year, tract)` to `get(tract, year=None)` now that
  `year` is optional, matching the backend, which now defaults it
  server-side to 2020 instead of requiring it in the URL path.
- **Breaking**: `sjvair calenviroscreen` is replaced by
  `sjvair calenviroscreen4` and `sjvair calenviroscreen5`. `--year` is now
  optional on `calenviroscreen4` (was required).
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for calenviroscreen4/5 and calheatscore"
```

---

### Task 8: Final verification

**Files:** none (verification only)

**Interfaces:** Consumes everything from Tasks 1-7.

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest`
Expected: All tests pass (no `-m live` tests run by default).

- [ ] **Step 2: Run the linter**

Run: `uv run ruff check sjvair/`
Expected: No errors. If there are formatting issues, run `uv run ruff format sjvair/` and re-check.

- [ ] **Step 3: Run the type checker**

Run: `uv run ty check sjvair/`
Expected: No new errors introduced by this work (pre-existing unrelated errors, if any, are out of scope).

- [ ] **Step 4: Manually smoke-test both new CLI commands against the mocked base URL is not possible (no live backend yet, PRs 247/254 unmerged) — instead verify `--help` output is well-formed**

Run: `uv run sjvair calenviroscreen4 --help && uv run sjvair calenviroscreen5 --help && uv run sjvair calheatscore --help`
Expected: Each prints usage/options text with no traceback. `calenviroscreen5 --help` must NOT list a `--year` option.

- [ ] **Step 5: Confirm the old bare command/attribute are fully gone**

Run: `uv run sjvair calenviroscreen --help; echo "exit code: $?"`
Expected: `Error: No such command 'calenviroscreen'.` and a non-zero exit code.

Run: `grep -rn "client.calenviroscreen\b" docs/ sjvair/ --include="*.py" --include="*.md" | grep -v "calenviroscreen4\|calenviroscreen5"`
Expected: No output (no stray references to the removed bare attribute).
