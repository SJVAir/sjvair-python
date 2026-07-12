# CLI Docs: Environment, Shell Completion, Troubleshooting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document three CLI behaviors that already work today with zero code changes: env-var/`.env` configuration, shell completion, and a new troubleshooting page covering retry/rate-limit behavior, region-name ambiguity, basemap tile flakiness, and GIF size.

**Architecture:** Two new sections appended to the existing `docs/cli/usage.md`, plus one new standalone page (`docs/cli/troubleshooting.md`) wired into the site's toctree in `docs/index.md`. No source code changes — this is a documentation-only plan. "Tests" here are a clean Sphinx build plus grepping the rendered output for the expected content.

**Tech Stack:** MyST Markdown, Sphinx (`sphinx-tabs` for the bash/zsh/fish and bash/powershell tab groups), built via `.venv/bin/python -m sphinx -b html docs docs/_build/html`.

## Global Constraints

- No source code changes in this plan — every behavior documented here was already verified working during the design phase (env-var propagation via Click's `envvar=`, `.env` auto-loading via `load_dotenv()`, and `_SJVAIR_COMPLETE` completion generation for bash/zsh/fish).
- Match the existing doc style: terse, example-first, using `::::{tabs}` / `:::{code-tab}` for OS- or shell-specific commands exactly as the rest of `docs/cli/` already does.
- Design doc: `docs/superpowers/specs/2026-07-11-cli-docs-env-completion-troubleshooting-design.md` — follow it exactly; this plan implements it task-for-task.
- **Note on this plan's own formatting:** several steps below show file content that itself contains fenced code blocks (bash examples, a `{toctree}` block). Those steps are wrapped in four-backtick (` ```` `) fences specifically so the inner triple-backtick fences display correctly instead of prematurely closing the outer block. When copying content out of a four-backtick-wrapped step, copy only what's between the ```` ```` ```` markers — the inner triple-backtick fences are part of the real file content and must be preserved as-is.

---

### Task 1: Environment and shell completion sections in `docs/cli/usage.md`

**Files:**
- Modify: `docs/cli/usage.md`

**Interfaces:** None — pure content addition, no other file depends on this task's output.

- [ ] **Step 1: Insert the "Environment" section**

Open `docs/cli/usage.md`. Find this exact text (the end of the "Region filters" section and start of "Entry types"):

```markdown
## Region filters

Wherever a command accepts a location, these flags resolve to a region and scope the results. Use at most one:

`--county` · `--city` · `--zip` · `--tract` (FIPS) · `--urban` (urban-area name) · `--region-id` (region ID)

## Entry types
```

Replace it with (inserting the new "Environment" and "Shell completion" sections between "Region filters" and "Entry types"):

`````markdown
## Region filters

Wherever a command accepts a location, these flags resolve to a region and scope the results. Use at most one:

`--county` · `--city` · `--zip` · `--tract` (FIPS) · `--urban` (urban-area name) · `--region-id` (region ID)

## Environment

Every global flag has a matching environment variable, so you can set them once instead of repeating them on every command:

| Flag | Environment variable | Default |
|---|---|---|
| `--base-url` | `SJVAIR_BASE_URL` | `https://www.sjvair.com/api/2.0/` |
| `--api-key` | `SJVAIR_API_KEY` | *(none — public endpoints work without one)* |
| `--timeout` | `SJVAIR_TIMEOUT` | `30` seconds |
| `--tz` | `SJVAIR_TZ` | *(none — naive timestamps are treated as UTC)* |

A `.env` file in the current directory is loaded automatically — no flag needed to enable it. This is the easiest way to stop passing `--tz` on every [timestamp-bearing command](#timestamps):

```bash
# .env
SJVAIR_TZ=America/Los_Angeles
```

```bash
# --tz is no longer needed -- SJVAIR_TZ from .env applies automatically
sjvair map create --type pm25 --county Fresno --timestamp "2026-07-04 20:30:00" --output fresno.png
```

## Shell completion

`sjvair` supports tab completion for commands and options, provided by the underlying [Click](https://click.palletsprojects.com/) framework — nothing extra to install beyond `sjvair` itself.

::::{tabs}

:::{code-tab} bash Bash
_SJVAIR_COMPLETE=bash_source sjvair > ~/.sjvair-complete.bash
echo '. ~/.sjvair-complete.bash' >> ~/.bashrc
:::

:::{code-tab} bash Zsh
_SJVAIR_COMPLETE=zsh_source sjvair > ~/.sjvair-complete.zsh
echo '. ~/.sjvair-complete.zsh' >> ~/.zshrc
:::

:::{code-tab} fish Fish
_SJVAIR_COMPLETE=fish_source sjvair > ~/.config/fish/completions/sjvair.fish
:::

::::

Restart your shell (or re-source the rc file) afterward. To try it out first without installing anything:

```bash
eval "$(_SJVAIR_COMPLETE=bash_source sjvair)"
```

## Entry types
`````

Use the Edit tool with the "Find this exact text" block as `old_string` and the replacement block as `new_string` (the four-backtick fence above is this plan document's wrapper, not part of the file content — copy everything between it, including the inner triple-backtick `bash` blocks, as the literal replacement text).

- [ ] **Step 2: Verify the two new headings and both code samples are present**

Run:

```bash
grep -c "^## Environment$" docs/cli/usage.md
grep -c "^## Shell completion$" docs/cli/usage.md
grep -c "SJVAIR_TZ=America/Los_Angeles" docs/cli/usage.md
grep -c "_SJVAIR_COMPLETE=fish_source" docs/cli/usage.md
```

Expected: each command prints `1`.

- [ ] **Step 3: Build the docs and confirm no new warnings**

Run:

```bash
.venv/bin/python -m sphinx -b html docs docs/_build/html -q 2>&1 | tail -40
```

Expected: no output (a clean build produces nothing on stdout/stderr in `-q` mode; this project's docs build has been warning-free throughout, so any output here is a regression to fix before continuing).

- [ ] **Step 4: Spot-check the rendered page**

Run:

```bash
grep -o '<h2>Environment[^<]*</h2>\|<h2>Shell completion[^<]*</h2>' docs/_build/html/cli/usage.html
```

Expected: both `<h2>Environment...` and `<h2>Shell completion...` lines print (exact surrounding markup may vary — the check is that both headings rendered).

- [ ] **Step 5: Commit**

```bash
git add docs/cli/usage.md
git commit -m "docs: document .env/environment-variable config and shell completion"
```

---

### Task 2: New `docs/cli/troubleshooting.md` page, wired into the nav

**Files:**
- Create: `docs/cli/troubleshooting.md`
- Modify: `docs/index.md`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: a reachable page at `cli/troubleshooting` other docs/specs can link to (the upcoming `regions search` sub-project's docs update should cross-link back here once it lands, but that's out of scope for this task).

- [ ] **Step 1: Create the troubleshooting page**

Write `docs/cli/troubleshooting.md` with exactly this content:

`````markdown
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
`````

The four-backtick fence above is this plan document's wrapper, not part of the file — write everything between it (starting at `# Troubleshooting`, ending after the GIF output size paragraph) as the literal content of the new file, including the inner triple-backtick block around the `Error: Ambiguous region...` example.

- [ ] **Step 2: Register the page in the site nav**

Open `docs/index.md`. Find this exact text:

````markdown
```{toctree}
:caption: Commands
:hidden:

cli/usage
cli/data-export/index
cli/maps/index
```
````

Replace it with:

````markdown
```{toctree}
:caption: Commands
:hidden:

cli/usage
cli/troubleshooting
cli/data-export/index
cli/maps/index
```
````

Use the Edit tool with the "Find this exact text" block as `old_string` and the replacement block as `new_string` (the four-backtick fence is this plan's wrapper; the real file content is the inner triple-backtick `{toctree}` block, unchanged apart from the added `cli/troubleshooting` line).

- [ ] **Step 3: Verify the page content and nav wiring**

Run:

```bash
grep -c "^# Troubleshooting$" docs/cli/troubleshooting.md
grep -c "^## Retries and rate limiting$" docs/cli/troubleshooting.md
grep -c "^## Region name ambiguity$" docs/cli/troubleshooting.md
grep -c "^## Map and timelapse basemap fetches can be flaky$" docs/cli/troubleshooting.md
grep -c "^## GIF output size$" docs/cli/troubleshooting.md
grep -c "cli/troubleshooting" docs/index.md
```

Expected: each command prints `1`.

- [ ] **Step 4: Build the docs and confirm no warnings, including no broken-link warnings**

Run:

```bash
.venv/bin/python -m sphinx -b html docs docs/_build/html -q 2>&1 | tail -60
```

Expected: no output. In particular, watch for any `WARNING: 'myst' cross-reference target not found` mentioning `troubleshooting` or `timelapse.md#timelapse-create` — both targets exist (the page just created, and the pre-existing `` ## `timelapse create` `` heading in `docs/cli/maps/timelapse.md`, confirmed to render as `<section id="timelapse-create">` in the current build), so no such warning should appear.

- [ ] **Step 5: Spot-check the rendered page and nav**

Run:

```bash
test -f docs/_build/html/cli/troubleshooting.html && echo "page built"
grep -o 'href="cli/troubleshooting.html"' docs/_build/html/index.html
```

Expected: `page built` prints, and the `href` grep prints one match (confirming the page is linked from the site's landing/nav, not just built as an orphan file).

- [ ] **Step 6: Commit**

```bash
git add docs/cli/troubleshooting.md docs/index.md
git commit -m "docs: add troubleshooting page covering retries, region ambiguity, tile flakiness, GIF size"
```
