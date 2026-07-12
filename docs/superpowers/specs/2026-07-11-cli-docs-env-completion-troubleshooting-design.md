# CLI Docs: Environment, Shell Completion, Troubleshooting — Design

**Date:** 2026-07-11
**Status:** Approved (pending spec review)

## Goal

Close three documentation gaps found during a docs/feature audit: the CLI's global
env-var/`.env` support, Click's built-in shell completion, and a troubleshooting page
covering behavior users are likely to hit but can't currently find documented anywhere.
All three already work today with zero code changes — this is a documentation-only
sub-project, the first of three from the audit (the other two, a `regions search`/
`lookup` command and a `--jobs` concurrency option, get their own specs).

Verified working during exploration (informs what the docs can truthfully claim):

- Setting `SJVAIR_TZ` in the environment (including via a `.env` file, auto-loaded by
  `load_dotenv()` in `cli/main.py`) populates `ctx.tz` through Click's `envvar=`
  mechanism — confirmed with a `CliRunner` test hitting a throwaway command.
- `_SJVAIR_COMPLETE=bash_source sjvair` (and the `zsh_source`/`fish_source` variants)
  correctly emit a completion script — Click's standard mechanism, no custom code.
- `SJVAirClient` retries 5x with exponential backoff on 5xx, and on 429 triggers a
  shared `CooldownGate` that blocks all threads until the wait clears — both read
  directly from `sjvair/client.py`.

## Decisions

| Decision | Choice |
|---|---|
| `.env`/env-var docs | New "Environment" section in `docs/cli/usage.md` |
| Shell completion docs | New "Shell completion" section in `docs/cli/usage.md`, same page |
| Troubleshooting content | New standalone page, `docs/cli/troubleshooting.md`, linked from CLI nav |
| Troubleshooting topics | Retry/rate-limit behavior; region-name ambiguity; map/timelapse tile-fetch flakiness; GIF size (short + link, no duplication) |
| Code changes | None — every behavior documented here already exists and works |

## `docs/cli/usage.md` — "Environment" section

Placed after the existing "Region filters" section. Content:

- A table of all four global env vars the CLI reads, each backing a global flag:
  `SJVAIR_BASE_URL` (`--base-url`), `SJVAIR_API_KEY` (`--api-key`), `SJVAIR_TIMEOUT`
  (`--timeout`), `SJVAIR_TZ` (`--tz`).
- A note that a `.env` file in the current directory is loaded automatically (no flag
  needed) — sourced from `load_dotenv()` in `cli/main.py`.
- A concrete example: a `.env` file containing `SJVAIR_TZ=America/Los_Angeles`, paired
  with a command that omits `--tz` entirely, to make the "set it once, stop repeating
  `--tz` on every invocation" payoff obvious — this is the specific case the user
  wants confirmed working.

## `docs/cli/usage.md` — "Shell completion" section

Placed after "Environment". Content:

- One-line explanation that completion is provided by the underlying Click framework,
  keyed off the installed script name (`sjvair`).
- Install snippets for bash, zsh, and fish (the three Click supports), each showing
  the `_SJVAIR_COMPLETE=<shell>_source sjvair` invocation piped into the shell's rc
  file, plus a note to restart the shell or re-source the rc file.
- A one-off "try without installing" line for people who just want to confirm it works
  first (eval the generated script in the current shell).

## New page: `docs/cli/troubleshooting.md`

Added to the CLI toctree (alongside `usage.md`, `reference.md`, etc.). Four sections,
each short (a paragraph or two, matching the terse style of the rest of the CLI docs):

1. **Retries and rate limiting** — what happens on a 5xx (up to 5 retries, exponential
   backoff) and on a 429 (shared cooldown that pauses all in-flight requests, not just
   the one that got limited); mentions `--timeout`/`SJVAIR_TIMEOUT` as the main
   user-facing knob, and that persistent 5xx/429s raise `ServerError`/`RateLimited`
   after retries are exhausted.
2. **Region name ambiguity** — `--urban`/`--county`/etc. shortcuts resolve by name and
   can match more than one region (real example: `--urban Hanford` also matches
   `Waterford`); shows the resulting error and points at `sjvair regions search` (new
   command, landing in the next sub-project) and `--region-id` as the fix. This section
   references a command that doesn't exist yet as of this doc landing — acceptable
   since the two sub-projects land in immediate sequence and this page isn't published
   independently before then.
3. **Map/timelapse basemap fetches can be flaky** — contextily's OpenStreetMap tile
   fetches occasionally fail with connection/SSL errors; this is transient upstream
   behavior, not a bug. Explains that `timelapse create` writes numbered frames to
   `--frames-dir` and skips ones that already exist, so re-running the same command
   after a failure is cheap and resumes instead of starting over.
4. **GIF output size** — two sentences and a link to the existing detailed guidance in
   `docs/cli/maps/timelapse.md` (the `--width`/`--height`/`--interval` sizing advice
   and in-CLI size warning already documented there) — no duplication.

## Testing

None needed — no code changes. Verification is: docs build cleanly with Sphinx
(`sphinx-build -b html`, already run this way throughout this project), and a manual
read-through that the documented commands/env vars/behavior match what's actually in
the code (the exploration above already confirmed the three load-bearing claims).
