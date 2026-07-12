# `regions search` CLI Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `sjvair regions search QUERY` — a CLI command that lists candidate regions matching a free-text name, printing a human-readable table by default (or CSV/JSON/YAML via `--format`/`--output`), so users can resolve the CLI's existing "Ambiguous region" error without guessing IDs blind.

**Architecture:** One new CLI command file (`sjvair/cli/commands/regions/search.py`) registered alongside the existing `regions list`/`get`/`summaries` commands. It reuses the existing `RegionsResource.search()` client method (no client changes) and a newly-extracted `format_region_table()` helper in `sjvair/cli/utils.py`, which also replaces the inline formatting `resolve_region()` already uses for its "Ambiguous region" error — a pure extraction that both commands now share.

**Tech Stack:** Python, Click (CLI framework), `responses` (HTTP mocking in tests), `pytest`.

## Global Constraints

- Command shape: `sjvair regions search QUERY [--type TYPE] [--output PATH] [--format {csv,json,yaml}]`. `QUERY` is a required positional argument. `--format` is a `click.Choice(['csv', 'json', 'yaml'])`, matching every other list-style command's `--format` option exactly (e.g. `sjvair/cli/commands/regions/list.py:20`).
- `--type` omitted → query exactly these 5 types, one API call each, in this order, results concatenated in this order: `('county', 'city', 'zipcode', 'tract', 'urban_area')`.
- `--type all` → one API call with no `type` param at all (`client.regions.search(query)`).
- `--type <anything else>` → one API call scoped to exactly that value (`client.regions.search(query, type=region_type)`); no `click.Choice` constraint on the value, matching `regions_list`'s existing unconstrained `--type`.
- Zero total results (across whichever mode ran) → `click.ClickException(f"No regions found matching {query!r}")` — this exact f-string, matching `resolve_region()`'s existing wording verbatim.
- Neither `--format` nor `--output` given → print `format_region_table(results)` via `click.echo` and stop. `boundary` is never touched on this path (the formatter only reads `id`/`type`/`name`).
- `--format` and/or `--output` given → strip the `boundary` key from every result dict, then call the existing `write_output(data, fmt, output_path, force=ctx.force)` / `format_from_path(output_path, fmt)` exactly as `regions_list` does.
- `format_region_table(results: list[dict[str, Any]]) -> str` lives in `sjvair/cli/utils.py`:
  ```python
  def format_region_table(results: list[dict[str, Any]]) -> str:
      return '\n'.join(f'  {r["id"]:36s}  {r.get("type", ""):<12}  {r["name"]}' for r in results)
  ```
  `resolve_region()`'s "Ambiguous region" error is refactored to call this instead of building its own `lines` list — the produced string must be byte-for-byte identical to what it raises today.
- No `regions lookup` CLI command is being added (out of scope, decided during brainstorming).
- No change to `docs/cli/troubleshooting.md` — its existing `sjvair regions search <name>` example already matches the final default-mode behavior.
- Design doc: `docs/superpowers/specs/2026-07-11-regions-search-command-design.md` — follow it exactly; this plan implements it task-for-task.

---

### Task 1: Extract `format_region_table()`, refactor `resolve_region()`, close its test gap

**Files:**
- Modify: `sjvair/cli/utils.py:85-118` (the `resolve_region` function)
- Test: `tests/test_cli/test_regions.py`

**Interfaces:**
- Produces: `format_region_table(results: list[dict[str, Any]]) -> str` in `sjvair/cli/utils.py`, importable as `from ...utils import format_region_table` from any file under `sjvair/cli/commands/*/`.

- [ ] **Step 1: Write a characterization test for the current (pre-refactor) "Ambiguous region" error**

This function currently has **no test coverage at all** (confirmed: nothing in the repo references `"Ambiguous"`, and `test_regions.py`'s existing `test_two_region_flags_is_an_error` only covers `resolve_region()`'s *other* error, "Only one region filter may be specified at a time"). This step locks down today's exact output before touching the code, so the refactor in Step 3 can be verified as byte-identical.

Add this test to `tests/test_cli/test_regions.py`, immediately after the existing `test_two_region_flags_is_an_error` function:

```python
@rsps.activate
def test_urban_flag_ambiguous_match_lists_candidates():
    rsps.add(
        rsps.GET,
        BASE + 'regions/places/search/',
        json={
            'data': [
                {'id': 'zvnca', 'name': 'Hanford', 'type': 'urban_area'},
                {'id': 'k3net', 'name': 'Waterford', 'type': 'urban_area'},
            ]
        },
    )
    result = CliRunner().invoke(cli, ['monitors', 'list', '--urban', 'Hanford'])
    assert result.exit_code != 0
    assert (
        "Ambiguous region 'Hanford' — 2 matches. Re-run with --region-id:\n"
        "  zvnca                                 urban_area    Hanford\n"
        "  k3net                                 urban_area    Waterford"
    ) in result.output
```

This dispatches through `monitors list --urban` (not a `regions` command) because `resolve_region()` is shared plumbing invoked by several commands — the existing `test_two_region_flags_is_an_error` in this same file already establishes that convention (it also dispatches through `monitors list`).

- [ ] **Step 2: Run the test to confirm it passes against today's code**

Run: `.venv/bin/python -m pytest tests/test_cli/test_regions.py::test_urban_flag_ambiguous_match_lists_candidates -v`

Expected: PASS. This is not a RED step — the behavior already exists; this step proves the test correctly characterizes it before anything changes.

- [ ] **Step 3: Extract `format_region_table()` and refactor `resolve_region()` to use it**

In `sjvair/cli/utils.py`, add this function directly above `resolve_region`:

```python
def format_region_table(results: list[dict[str, Any]]) -> str:
    return '\n'.join(f'  {r["id"]:36s}  {r.get("type", ""):<12}  {r["name"]}' for r in results)


def resolve_region(
```

Then change the end of `resolve_region` (currently lines 113-118) from:

```python
    if len(results) == 1:
        return results[0]['id']
    lines = [f'  {r["id"]:36s}  {r.get("type", ""):<12}  {r["name"]}' for r in results]
    raise click.ClickException(
        f'Ambiguous region {query!r} — {len(results)} matches. Re-run with --region-id:\n' + '\n'.join(lines)
    )
```

to:

```python
    if len(results) == 1:
        return results[0]['id']
    raise click.ClickException(
        f'Ambiguous region {query!r} — {len(results)} matches. Re-run with --region-id:\n'
        + format_region_table(results)
    )
```

- [ ] **Step 4: Run the same test again to confirm the refactor didn't change the output**

Run: `.venv/bin/python -m pytest tests/test_cli/test_regions.py::test_urban_flag_ambiguous_match_lists_candidates -v`

Expected: PASS, unchanged.

- [ ] **Step 5: Run the full CLI test suite to confirm nothing else broke**

Run: `.venv/bin/python -m pytest tests/ -q --no-cov -m "not live"`

Expected: all tests pass (this repo's suite was at 149 passed, 2 skipped before this change on `main`; expect 150 passed, 2 skipped — one net new test — modulo any other in-progress uncommitted work in the checkout you're running this in).

- [ ] **Step 6: Commit**

```bash
git add sjvair/cli/utils.py tests/test_cli/test_regions.py
git commit -m "refactor: extract format_region_table(), close ambiguous-region test gap"
```

---

### Task 2: `sjvair regions search` command

**Files:**
- Create: `sjvair/cli/commands/regions/search.py`
- Modify: `sjvair/cli/commands/regions/__init__.py`
- Test: `tests/test_cli/test_regions.py`

**Interfaces:**
- Consumes: `format_region_table(results: list[dict[str, Any]]) -> str`, `format_from_path(output: Path | None, fmt: str | None) -> str`, `write_output(data, fmt, output, force=False) -> None` — all from `sjvair/cli/utils.py` (the first added by Task 1; the other two already exist). Consumes `ctx.client.regions.search(query: str, **params: Any) -> list[dict[str, Any]]` (already exists, unchanged) and `ctx.force: bool` (from `_ClientContext`, already exists).
- Produces: the `regions_search` Click command, registered as `sjvair regions search`.

- [ ] **Step 1: Write the failing tests**

Add these to `tests/test_cli/test_regions.py` (append at the end of the file):

```python
@rsps.activate
def test_regions_search_default_type_queries_five_shortcut_types_and_merges():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r1', 'name': 'A County', 'type': 'county'}]})
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r2', 'name': 'A City', 'type': 'city'}]})
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': []})
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': []})
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'r3', 'name': 'A Urban', 'type': 'urban_area'}]})

    result = CliRunner().invoke(cli, ['regions', 'search', 'A'])

    assert result.exit_code == 0, result.output
    assert len(rsps.calls) == 5
    expected_types = ['county', 'city', 'zipcode', 'tract', 'urban_area']
    for call, expected_type in zip(rsps.calls, expected_types):
        assert f'type={expected_type}' in call.request.url

    lines = result.output.splitlines()
    assert 'r1' in lines[0] and 'A County' in lines[0]
    assert 'r2' in lines[1] and 'A City' in lines[1]
    assert 'r3' in lines[2] and 'A Urban' in lines[2]


@rsps.activate
def test_regions_search_specific_type_issues_one_request():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'zvnca', 'name': 'Hanford', 'type': 'urban_area'}]})

    result = CliRunner().invoke(cli, ['regions', 'search', 'Hanford', '--type', 'urban_area'])

    assert result.exit_code == 0, result.output
    assert len(rsps.calls) == 1
    assert 'type=urban_area' in rsps.calls[0].request.url
    assert 'Hanford' in result.output


@rsps.activate
def test_regions_search_type_all_issues_untyped_request():
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'zvnca', 'name': 'Hanford', 'type': 'urban_area'}]})

    result = CliRunner().invoke(cli, ['regions', 'search', 'Hanford', '--type', 'all'])

    assert result.exit_code == 0, result.output
    assert len(rsps.calls) == 1
    assert 'type=' not in rsps.calls[0].request.url


@rsps.activate
def test_regions_search_default_output_is_a_table():
    for _ in range(4):
        rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': []})
    rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': [{'id': 'zvnca', 'name': 'Hanford', 'type': 'urban_area'}]})

    result = CliRunner().invoke(cli, ['regions', 'search', 'Hanford'])

    assert result.exit_code == 0, result.output
    assert result.output == '  zvnca                                 urban_area    Hanford\n'


@rsps.activate
def test_regions_search_format_csv_strips_boundary_field():
    rsps.add(
        rsps.GET,
        BASE + 'regions/places/search/',
        json={
            'data': [
                {
                    'id': 'zvnca',
                    'name': 'Hanford',
                    'slug': 'hanford',
                    'type': 'urban_area',
                    'boundary': {'type': 'MultiPolygon', 'coordinates': [[[[1, 2]]]]},
                },
            ]
        },
    )

    result = CliRunner().invoke(cli, ['regions', 'search', 'Hanford', '--type', 'urban_area', '--format', 'csv'])

    assert result.exit_code == 0, result.output
    assert 'boundary' not in result.output
    assert result.output.splitlines()[0] == 'id,name,slug,type'
    assert 'zvnca,Hanford,hanford,urban_area' in result.output


@rsps.activate
def test_regions_search_no_matches_raises_error():
    for _ in range(5):
        rsps.add(rsps.GET, BASE + 'regions/places/search/', json={'data': []})

    result = CliRunner().invoke(cli, ['regions', 'search', 'Nonexistent'])

    assert result.exit_code != 0
    assert "No regions found matching 'Nonexistent'" in result.output
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_cli/test_regions.py -k "regions_search" -v`

Expected: FAIL for all 6 — `regions search` is not yet a registered command, so Click will report "No such command 'search'" (non-zero exit, but not matching the test bodies' further assertions since those never get reached / the mocked HTTP calls never fire).

- [ ] **Step 3: Create `sjvair/cli/commands/regions/search.py`**

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from ...main import _ClientContext, pass_ctx
from ...utils import format_from_path, format_region_table, write_output

DEFAULT_TYPES = ('county', 'city', 'zipcode', 'tract', 'urban_area')


@click.command('search')
@click.argument('query')
@click.option(
    '--type',
    'region_type',
    default=None,
    help='Region type to search. Omit to search county/city/zipcode/tract/urban_area '
    '(the same types the --county/--city/--zip/--tract/--urban shortcuts resolve to). '
    'Pass "all" to search every region type without filtering.',
)
@click.option('--output', 'output_path', type=click.Path(path_type=Path), default=None)
@click.option('--format', 'fmt', type=click.Choice(['csv', 'json', 'yaml']), default=None)
@pass_ctx
def regions_search(
    ctx: _ClientContext,
    query: str,
    region_type: str | None,
    output_path: Path | None,
    fmt: str | None,
) -> None:
    """Search regions by name. Prints a table by default; pass --output/--format for CSV/JSON/YAML."""
    results: list[dict[str, Any]]
    if region_type == 'all':
        results = ctx.client.regions.search(query)
    elif region_type:
        results = ctx.client.regions.search(query, type=region_type)
    else:
        results = []
        for region_search_type in DEFAULT_TYPES:
            results.extend(ctx.client.regions.search(query, type=region_search_type))

    if not results:
        raise click.ClickException(f'No regions found matching {query!r}')

    if fmt is None and output_path is None:
        click.echo(format_region_table(results))
        return

    data = ({k: v for k, v in r.items() if k != 'boundary'} for r in results)
    fmt = format_from_path(output_path, fmt)
    write_output(data, fmt, output_path, force=ctx.force)
```

- [ ] **Step 4: Register the command**

In `sjvair/cli/commands/regions/__init__.py`, change:

```python
from .get import regions_get
from .list import regions_list
from .summaries import regions_summaries


@click.group('regions')
def regions() -> None:
    """Region data commands."""


regions.add_command(regions_list, 'list')
regions.add_command(regions_get, 'get')
regions.add_command(regions_summaries, 'summaries')
```

to:

```python
from .get import regions_get
from .list import regions_list
from .search import regions_search
from .summaries import regions_summaries


@click.group('regions')
def regions() -> None:
    """Region data commands."""


regions.add_command(regions_list, 'list')
regions.add_command(regions_search, 'search')
regions.add_command(regions_get, 'get')
regions.add_command(regions_summaries, 'summaries')
```

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_cli/test_regions.py -k "regions_search" -v`

Expected: all 6 PASS.

- [ ] **Step 6: Run the full test suite**

Run: `.venv/bin/python -m pytest tests/ -q --no-cov -m "not live"`

Expected: all tests pass (150 passed + 2 skipped from Task 1, plus these 6 new ones — expect 156 passed, 2 skipped, modulo any other in-progress uncommitted work in the checkout).

- [ ] **Step 7: Commit**

```bash
git add sjvair/cli/commands/regions/search.py sjvair/cli/commands/regions/__init__.py tests/test_cli/test_regions.py
git commit -m "feat: add regions search CLI command"
```

---

### Task 3: Document `regions search`

**Files:**
- Modify: `docs/cli/data-export/regions.md`

**Interfaces:** None — pure documentation, no other file depends on this task's output.

- [ ] **Step 1: Insert a `## regions search` section between `regions list` and `regions get`**

Find this exact text in `docs/cli/data-export/regions.md`:

```markdown
```bash
sjvair regions list --type city --county Fresno --output cities.csv
```

## `regions get`
```

Replace it with:

`````markdown
```bash
sjvair regions list --type city --county Fresno --output cities.csv
```

## `regions search`

Search regions by name — useful for finding a region's ID, or for seeing every candidate up front when a shortcut flag (`--county`/`--city`/`--zip`/`--tract`/`--urban`) would otherwise fail with an "Ambiguous region" error. Prints a table by default; pass `--output` or `--format` for CSV/JSON/YAML instead.

Without `--type`, searches the same 5 types the shortcut flags resolve to (`county`, `city`, `zipcode`, `tract`, `urban_area`):

```bash
sjvair regions search Hanford
```

```
  77yxc                                 city          Hanford
  crnag                                 city          Waterford
  zvnca                                 urban_area    Hanford
  k3net                                 urban_area    Waterford
```

Scope to one type:

```bash
sjvair regions search Fresno --type county
```

Search every region type, including ones the shortcut flags never use (`protected`, `school_district`, etc.):

```bash
sjvair regions search Hanford --type all
```

Get structured output instead of the table:

```bash
sjvair regions search Hanford --format csv
```

## `regions get`
`````

Use the Edit tool with the "Find this exact text" block as `old_string` and the replacement block as `new_string` (the five-backtick fence above is this plan document's wrapper, not part of the file content — copy everything between it as the literal replacement text, including the inner triple-backtick `bash` and plain-text blocks).

- [ ] **Step 2: Verify the new section is present**

Run:

```bash
grep -c "^## \`regions search\`$" docs/cli/data-export/regions.md
grep -c "sjvair regions search Hanford --type all" docs/cli/data-export/regions.md
grep -c "sjvair regions search Hanford --format csv" docs/cli/data-export/regions.md
```

Expected: each command prints `1`.

- [ ] **Step 3: Build the docs and confirm no new warnings**

Run:

```bash
.venv/bin/python -m sphinx -b html docs docs/_build/html -q 2>&1 | tail -40
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add docs/cli/data-export/regions.md
git commit -m "docs: document regions search command"
```
