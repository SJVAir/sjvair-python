# Troubleshooting

## Retries and rate limiting

`SJVAirClient` (used by both the CLI and the Python library) retries failed requests automatically:

- **Server errors (5xx)** are retried up to 5 times with exponential backoff (1s, 2s, 4s, 8s, 16s) before raising `sjvair.exceptions.ServerError`.
- **Rate limiting (429)** triggers a shared cooldown — every in-flight and subsequent request waits until it clears, not just the one that got limited. The cooldown starts from the server's `Retry-After` header (or 60s if it's absent) and doubles on each subsequent 429, up to 5 retries, before raising `sjvair.exceptions.RateLimited`.

`--timeout`/`SJVAIR_TIMEOUT` (default 30 seconds) is the main knob available if requests are timing out rather than erroring; there's currently no CLI flag to change the retry count.

## Region name ambiguity

`--county`, `--city`, `--zip`, `--tract`, and `--urban` all resolve a name to a region by searching, and that search can match more than one region. For example, `--urban Hanford` also matches `Waterford`:

```
Error: Ambiguous region 'Hanford' — 2 matches. Re-run with --region-id:
  zvnca                                 urban_area    Hanford
  k3net                                 urban_area    Waterford
```

Use `sjvair regions search <name>` to see candidate matches up front, then pass the exact ID via `--region-id` instead of a name shortcut.

## Map and timelapse basemap fetches can be flaky

`map create` and `timelapse create` fetch OpenStreetMap basemap tiles over the network (via `contextily`). These fetches occasionally fail with a connection or SSL error — this is transient upstream behavior, not a bug in `sjvair`.

For `timelapse create`, this is cheap to recover from: frames are written as numbered PNGs to `--frames-dir` (default `<output>.frames/`), and re-running the same command skips any frame that already exists on disk. If a run fails partway through, just run it again — it resumes instead of starting over.

## GIF output size

Animated GIFs have no real inter-frame compression, so file size scales with resolution and frame count. See [`timelapse create`](maps/timelapse.md#timelapse-create) for sizing guidance and the CLI's built-in size warning.
