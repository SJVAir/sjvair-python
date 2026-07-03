# Documentation Site — Design

**Date:** 2026-07-03
**Status:** Approved (pending spec review)

## Goal

Publish real documentation for the `sjvair` package — worked examples plus reference for
**both** the CLI and the Python client — auto-built and deployed to GitHub Pages. Reference
content is generated from the source (docstrings, click app) so it can't drift from the code.

## Decisions

| Decision | Choice |
|---|---|
| Toolchain | MkDocs + Material theme |
| API reference | `mkdocstrings[python]` from docstrings (Google style) |
| CLI reference | `mkdocs-click` from the click app |
| README relationship | README trimmed to install + quickstart + link; docs are the source of truth for depth |
| Pipeline | GitHub Actions-native deploy (`upload-pages-artifact` + `deploy-pages`), no gh-pages branch |
| Versioning | Single "latest" site (no `mike` yet — YAGNI until releases are pinned) |
| Changelog page | Keep (includes root `CHANGELOG.md` via snippet) |
| API reference layout | One page (client + all resource classes); split later if it grows |
| Domain | `https://SJVAir.github.io/sjvair-python/` now; custom domain later is a one-line change |

## Dependencies

New PEP 735 dependency group (dev-only, not shipped in the package):

```toml
[dependency-groups]
docs = ["mkdocs-material", "mkdocstrings[python]", "mkdocs-click"]
```

## Site structure

`docs_dir` is `docs/`. `docs/superpowers/` (internal specs/plans) is kept out of the
published site via MkDocs' native `exclude_docs`.

```
Home             docs/index.md            overview, install, short quickstart
CLI
  Guide          docs/cli/guide.md        narrative + worked examples per command (from README)
  Reference      docs/cli/reference.md    auto — mkdocs-click over the whole CLI tree
Python client
  Guide          docs/client/guide.md     client, resources, bulk export, output formats
  API reference  docs/client/reference.md auto — mkdocstrings for SJVAirClient + resources
Changelog        docs/changelog.md        includes root CHANGELOG.md via pymdownx snippet
```

Each track (CLI, client) is a hand-written **guide** (examples) plus an **auto-generated
reference**.

## Auto-generated reference

- **CLI** (`docs/cli/reference.md`): one `mkdocs_click` directive pointing at the click group
  `sjvair.cli.main:cli`; the full command tree + options render automatically.
- **API** (`docs/client/reference.md`): `::: sjvair.client.SJVAirClient` plus each resource
  class (`MonitorsResource`, `RegionsResource`, `CalEnviroScreenResource`, `CEIDARSResource`,
  `HMSResource`, `PesticidesResource`). mkdocstrings renders signatures + docstrings.

## `mkdocs.yml` (shape)

- `site_name`, `site_url` (github.io URL), `repo_url` → the repo
- `theme: material` with features: navigation tabs/sections, instant nav, code copy, search
- `plugins: [search, mkdocstrings]` — mkdocstrings python handler with
  `docstring_style: google`, `show_root_heading`, `show_source`
- `markdown_extensions`: `admonition`, `pymdownx.superfences`, `pymdownx.highlight`,
  `toc` (permalinks), `mkdocs_click`, `pymdownx.snippets` (for the changelog include)
- `exclude_docs: |` → `superpowers/`
- `nav`: as above

## Build & publish pipeline

New `.github/workflows/docs.yml`:

- **Trigger:** push to `main`
- **Permissions:** `pages: write`, `id-token: write`, `contents: read`
- **Concurrency:** a `pages` group so overlapping deploys don't race
- **Steps:** `checkout@v5` → `setup-uv@v8.2.0` → `uv sync --group docs` →
  `uv run mkdocs build --strict` → `actions/upload-pages-artifact` → `actions/deploy-pages`
  (environment `github-pages`)
- `--strict` fails the build on broken links / bad references — the CI gate for docs

**One-time manual step:** repo **Settings → Pages → Source: GitHub Actions**.

## README slimming

Trim README to: title, install, a ~15-line quickstart (one client snippet + a couple of CLI
commands), and a prominent link to the docs site. The exhaustive per-command tables/examples
move into `docs/cli/guide.md` and `docs/client/guide.md`.

## Local dev & validation

- Preview: `uv run mkdocs serve`
- CI gate: `uv run mkdocs build --strict`

## Custom domain (future, out of scope now)

Switching to `docs.sjvair.com` / `developer.sjvair.com` later: update `site_url`, add a
`docs/CNAME` file (or Pages custom-domain setting), and point DNS. No structural rework.

## Out of scope (YAGNI)

- `mike` version dropdown
- Custom domain (deferred to the future step above)
- Docs search analytics / social cards
