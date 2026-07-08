# Design: Migrate docs from MkDocs to Sphinx + MyST

## Context

The docs site (added in [[2026-07-03-docs-site-design]]) currently runs on
mkdocs-material. Upstream MkDocs 2.0 is a ground-up rewrite that drops plugin
support, changes the theming API, and switches config formats, with no
migration path from 1.x. `mkdocstrings` and `mkdocs-click` — both plugins —
and the `overrides/` theme customization this project relies on would break
under 2.0. Rather than gamble on the not-yet-stable "Zensical" compatibility
shim, we're moving to Sphinx, which is independently maintained and has no
single-vendor risk.

## Goal

Replace mkdocs-material with Sphinx, keeping all content in Markdown via
MyST, using `autodoc`/`autosummary` for the Python API reference,
`sphinx-click` for the CLI reference, and the Shibuya theme. Single clean
cutover — no interim period running both toolchains.

## Directory layout

Keep `docs/` as the Sphinx source root, matching the current MkDocs layout.
Add `docs/conf.py`. Build output goes to `docs/_build/html` (already covered
by the standard-template `docs/_build/` entry in `.gitignore`, left over from
before this project used docs tooling at all).

## Reference-page approach

`autodoc`/`autosummary` and `sphinx-click` only expose reStructuredText
directives, not native MyST syntax. To keep the "everything stays in
Markdown" requirement, `client/reference.md` and `cli/reference.md` remain
`.md` files, with the directive calls dropped into `` ```{eval-rst} `` fenced
blocks — MyST's documented escape hatch for RST-only extensions — rather than
converting those two pages to `.rst`. This confines RST to a few lines inside
two files instead of switching the whole reference section to a different
syntax.

## Content mapping

| mkdocs today | Sphinx equivalent |
|---|---|
| `nav:` in `mkdocs.yml` | `{toctree}` directive in `index.md` |
| `::: sjvair.client.SJVAirClient` (mkdocstrings) | `` ```{eval-rst}\n.. autoclass:: sjvair.client.SJVAirClient\n   :members:\n``` `` per class |
| `::: mkdocs-click` block | `` ```{eval-rst}\n.. click:: sjvair.cli.main:cli\n   :prog: sjvair\n   :nested: full\n``` `` |
| `--8<-- "CHANGELOG.md"` (pymdownx.snippets) | `` ```{include} ../CHANGELOG.md\n``` `` (MyST include directive) |
| `exclude_docs: superpowers/` | `exclude_patterns` in `conf.py` |
| `overrides/main.html` (favicon/meta tags) | `html_favicon` + `html_static_path` in `conf.py`, plus a minimal template override if Shibuya needs one for the extra meta tags |
| `dev_addr: localhost:8080` | `sphinx-autobuild docs docs/_build/html --port 8080` (new dev dependency) |

All five content pages (`index.md`, `cli/guide.md`, `cli/reference.md`,
`client/guide.md`, `client/reference.md`, `changelog.md`) carry over as-is
otherwise — none use Material-only Markdown extensions (no admonitions in
current content; fenced code blocks and tables are native MyST/CommonMark).

## Config/dependency changes

- `pyproject.toml`: replace the `docs` dependency group
  (`mkdocs-material`, `mkdocstrings[python]`, `mkdocs-click`) with `sphinx`,
  `myst-parser`, `sphinx-autobuild`, `shibuya`, `sphinx-click`
  (`autodoc`/`autosummary` ship in Sphinx core, no extra package)
- Delete `mkdocs.yml` and `overrides/` after porting anything needed into
  `conf.py`/templates
- `.github/workflows/docs.yml`: swap `mkdocs build --strict` for
  `sphinx-build -b html docs docs/_build/html -W` (`-W` = warnings-as-errors,
  mirroring `--strict`) and change the uploaded Pages artifact path to
  `docs/_build/html`

## Acceptance criteria

- `sphinx-build -W` completes with zero warnings/errors
- All 5 content pages render with working navigation
- API reference shows every class currently listed in `client/reference.md`
- CLI reference shows the full `sjvair` command tree
- Changelog page renders the included `CHANGELOG.md` content
- Site builds and serves locally via `sphinx-autobuild`
