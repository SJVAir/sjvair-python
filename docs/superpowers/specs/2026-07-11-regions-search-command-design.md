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

Exploration during brainstorming (all against the live API) found three
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

## Decisions

| Decision | Choice |
|---|---|
| Command | `sjvair regions search QUERY [--type TYPE] [--output PATH] [--format {csv,json,yaml}]` |
| `QUERY` | Required positional argument (matches `regions get REGION_ID`'s convention) |
| `--type` omitted | Search 5 types — `county`, `city`, `zipcode`, `tract`, `urban_area` — one API call each, results concatenated in that order |
| `--type <value>` | Single API call scoped to exactly that type (any of the 15 real region types, e.g. `protected`) |
| `--type all` | Single API call with no type filter — the full, unrestricted search. `"all"` is not a real region type value, so no collision. |
| Output fields | Every result has `boundary` stripped before formatting, regardless of `--format` |
| Output machinery | Reuses `write_output`/`format_from_path` exactly as `regions list` does — CSV to stdout by default, `--output`/`--format` behave identically |
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
5. Otherwise, strip the `boundary` key from every result dict, then call
   `write_output(data, fmt, output_path, force=ctx.force)` exactly as
   `regions_list` does (`fmt = format_from_path(output_path, fmt)` first).

`--type` itself is a plain string option (no `click.Choice` constraint) —
matching `regions_list`'s existing `--type`, which is also unconstrained.

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
- Output never contains a `boundary` field/column, in any format.
- Zero matches (all mocked calls return empty `data`) → non-zero exit code,
  `"No regions found matching"` in output.
- `--output`/`--format` behave identically to `regions list` (can reuse a
  minimal version of that existing test's shape rather than re-deriving
  `write_output` coverage from scratch — this command doesn't add any new
  branch to `write_output` itself).

## Docs

- `docs/cli/data-export/regions.md`: new `## regions search` section
  (matching the existing `## regions list` / `## regions get` /
  `## regions summaries` style), documenting all three modes with one
  example each: default, `--type <specific>`, `--type all`.
- `docs/cli/troubleshooting.md`: no change (confirmed above — its existing
  example already matches the final default-mode behavior).
