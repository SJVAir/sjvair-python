# `regions search` CLI Command — Design

**Date:** 2026-07-11
**Status:** Approved (pending spec review)

## Goal

Add `sjvair regions search QUERY` — a CLI command that lists candidate regions
matching a free-text name, so a user hitting the CLI's existing "Ambiguous
region" error (raised by `resolve_region()` in `sjvair/cli/utils.py` when a
`--county`/`--city`/`--zip`/`--tract`/`--urban` shortcut matches more than one
region) can see the candidates and their IDs up front instead of only after
the error fires. This is the second sub-project from a docs/feature audit
(the first, CLI env/completion docs + a troubleshooting page, already shipped
and references this command by name in
`docs/cli/troubleshooting.md`'s "Region name ambiguity" section).

`RegionsResource.search()`/`.lookup()` already exist on the Python client
(`sjvair/resources/regions.py`) and already back the shortcut flags — this
sub-project only adds a CLI command wrapping `search()`. No `lookup()`
wrapper is being added (decided during brainstorming): `search` alone covers
the concrete pain point, and `lookup()` remains available directly from the
Python client for scripting use.

## Investigation that shaped this design

Exploration during brainstorming (all against the live API) found four
things worth recording, since they're the reason the design isn't a
straight 1:1 CLI wrapper around `search()`:

1. **`search()` results carry the same full `boundary` GeoJSON polygon as
   `regions list`/`regions get`** (confirmed: `list(x.keys())` on a search
   result is `['id', 'name', 'slug', 'type', 'boundary']`, and `boundary` is
   a multi-hundred-coordinate nested structure). Dumped straight to CSV via
   the existing `write_output` machinery, that's an unusable wall of text
   per row. The CLI's own existing "Ambiguous region" error message already
   solves this by hand-formatting only `id`/`type`/`name` — this command
   follows that precedent by dropping `boundary` before output, for every
   format (CSV/JSON/YAML), not just CSV.
2. **An untyped search is too noisy to be useful.** `search('Hanford')` with
   no `type` returns 41 results (parks, school districts, unnamed sites);
   `search('Hanford', type='urban_area')` returns exactly 2. But restricting
   to the 5 types the CLI's own shortcut flags already resolve to —
   `county`, `city`, `zipcode`, `tract`, `urban_area` (the exact mapping
   `resolve_region()` encodes) — brings "Hanford" down to 4 relevant results
   (city: Hanford/Waterford, urban_area: Hanford/Waterford) with zero
   configuration from the user. This became the default behavior.
3. **The `/regions/places/search/` endpoint's `type` parameter is optional
   at the API level** (confirmed via the live OpenAPI spec:
   `required: false`, and empirically — an untyped call succeeds, just
   noisily). So "search everything" is a real, supported mode, not a
   workaround; it just isn't a good *default*.
4. **The CLI already has a table formatter for exactly this shape of data**,
   just not a shared/reusable one: `resolve_region()`'s ambiguous-region
   error hand-formats `id`/`type`/`name` as aligned columns
   (`f'  {r["id"]:36s}  {r.get("type", ""):<12}  {r["name"]}'`). Since this
   command produces the same shape of data for the same purpose (a human
   scanning candidates to pick one), it reuses that exact format as its
   default terminal output — extracted into a shared helper so both call
   sites render identically instead of maintaining two copies of the same
   formatting.

## Decisions

| Decision | Choice |
|---|---|
| Command | `sjvair regions search QUERY [--type TYPE] [--output PATH] [--format {csv,json,yaml}]` |
| `QUERY` | Required positional argument (matches `regions get REGION_ID`'s convention) |
| `--type` omitted | Search 5 types — `county`, `city`, `zipcode`, `tract`, `urban_area` — one API call each, results concatenated in that order |
| `--type <value>` | Single API call scoped to exactly that type (any of the 15 real region types, e.g. `protected`) |
| `--type all` | Single API call with no type filter — the full, unrestricted search. `"all"` is not a real region type value, so no collision. |
| Output fields | Every result has `boundary` stripped before formatting, regardless of `--format` |
| Default output (no `--format`/`--output`) | A human-readable table to stdout — the same `id`/`type`/`name` aligned format as the existing ambiguous-region error, via a new shared helper. Not CSV, unlike every other list-style command. |
| `--format`/`--output` given | Falls through to the existing `write_output`/`format_from_path` machinery exactly as `regions list` does — CSV/JSON/YAML, to stdout or a file |
| Shared table formatter | New `format_region_table(results)` in `sjvair/cli/utils.py`; `resolve_region()`'s ambiguous-region error is refactored to call it too, so both surfaces render identically and the format string exists in one place |
| Table header row | None — matches the existing ambiguous-region error's output exactly (decided during brainstorming) |
| Zero matches | `click.ClickException(f"No regions found matching {query!r}")` — identical wording to `resolve_region()`'s existing error |
| Deduplication | None needed — each of the 5 default-mode calls is scoped to a distinct type, and a region has exactly one type, so no ID can appear twice across them |
| `lookup()` CLI wrapper | Not added (decided during brainstorming) — out of scope |
| `docs/cli/troubleshooting.md` | No change needed — its existing example, `sjvair regions search <name>` (no `--type`), already works correctly under the final default-mode design |

## CLI: `sjvair regions search`

New file `sjvair/cli/commands/regions/search.py`, registered in
`sjvair/cli/commands/regions/__init__.py` alongside `list`/`get`/`summaries`.

```python
DEFAULT_TYPES = ('county', 'city', 'zipcode', 'tract', 'urban_area')
```

This constant mirrors the exact type mapping already implicit in
`resolve_region()`'s `--county`/`--city`/`--zip`/`--tract`/`--urban` handling
(`sjvair/cli/utils.py`) — it is not derived from that function
programmatically (the two are independent, small, and stable; introducing a
shared import for a 5-tuple used in exactly one place besides its own
already-inlined counterpart is not warranted).

Command flow:

1. If `--type` is `all`: one call, `client.regions.search(query)`.
2. Elif `--type` is given (anything else): one call,
   `client.regions.search(query, type=region_type)`.
3. Else (no `--type`): one call per entry in `DEFAULT_TYPES`,
   `client.regions.search(query, type=t)`, results concatenated in
   `DEFAULT_TYPES` order.
4. If the combined result list is empty, raise
   `click.ClickException(f"No regions found matching {query!r}")`.
5. If neither `--format` nor `--output` was given: print
   `format_region_table(results)` to stdout via `click.echo` and return —
   `boundary` is never touched on this path, since the table formatter only
   ever reads `id`/`type`/`name`.
6. Otherwise (`--format` and/or `--output` given): strip the `boundary` key
   from every result dict, then call
   `write_output(data, fmt, output_path, force=ctx.force)` exactly as
   `regions_list` does (`fmt = format_from_path(output_path, fmt)` first).

`--type` itself is a plain string option (no `click.Choice` constraint) —
matching `regions_list`'s existing `--type`, which is also unconstrained.

## Refactor: shared table formatter in `sjvair/cli/utils.py`

```python
def format_region_table(results: list[dict[str, Any]]) -> str:
    return '\n'.join(f'  {r["id"]:36s}  {r.get("type", ""):<12}  {r["name"]}' for r in results)
```

`resolve_region()`'s ambiguous-region error changes from building `lines`
inline to:

```python
raise click.ClickException(
    f'Ambiguous region {query!r} — {len(results)} matches. Re-run with --region-id:\n'
    + format_region_table(results)
)
```

This is a pure extraction — the produced string is byte-for-byte identical
to what `resolve_region()` already raises today. There is no existing test
locking that string down (see Testing below); the new test this task adds
is what proves the extraction didn't change it.

## Error handling

- Zero matches across whichever mode ran: `ClickException`, same wording as
  the existing ambiguous-region error path, so the two error surfaces read
  consistently.
- No new error paths beyond what `write_output` already handles (e.g.
  `--output` pointing at an existing file without `--force`).

## Testing

New tests in `tests/test_cli/test_regions.py` (existing file, existing
`responses`-mock + `CliRunner` pattern — see `test_regions_list`,
`test_city_flag_scopes_search_to_city_type` for the established style):

- Default mode (no `--type`) issues exactly 5 requests to
  `regions/places/search/`, one per `DEFAULT_TYPES` entry (assert on
  `type=` query param per call), and merges results in order.
- `--type urban_area` issues exactly 1 request with `type=urban_area`.
- `--type all` issues exactly 1 request with no `type` param.
- With neither `--format` nor `--output`: output matches
  `format_region_table()`'s exact formatting (aligned columns, no header,
  no `boundary`) — assert the literal expected string, not just substring
  presence.
- With `--format csv` (or `--output foo.json`, etc.): output never contains
  a `boundary` field/column, in any format — this is the pre-existing
  `write_output` path, unaffected by the table-default change.
- Zero matches (all mocked calls return empty `data`) → non-zero exit code,
  `"No regions found matching"` in output, regardless of whether `--format`
  was given (the empty-check happens before the table-vs-write_output
  branch).
- `resolve_region()`'s ambiguous-region error currently has **no test
  coverage** (confirmed: no test in the repo references "Ambiguous" or
  triggers a multi-match `resolve_region()` call — `test_regions.py`'s
  existing `test_two_region_flags_is_an_error` only covers the *other*
  `resolve_region()` error, "Only one region filter may be specified at a
  time"). Since this task extracts and reuses that error's exact formatting,
  add the missing test now: mock a `regions/places/search/` response with 2+
  results for a shortcut flag (e.g. `--urban`), assert the `ClickException`
  message matches the full expected string (the `Ambiguous region ...`
  prefix plus `format_region_table()`'s output) — this both closes a
  pre-existing gap and protects the refactor from silently changing output.

## Docs

- `docs/cli/data-export/regions.md`: new `## regions search` section
  (matching the existing `## regions list` / `## regions get` /
  `## regions summaries` style), documenting all three `--type` modes
  (default, `--type <specific>`, `--type all`) and the table-by-default /
  `--format`-or-`--output`-for-structured-data behavior, with at least one
  example showing the default table output and one showing `--format csv`
  or `--output`.
- `docs/cli/troubleshooting.md`: no change (confirmed above — its existing
  example already matches the final default-mode behavior).
