# Sphinx Docs Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace mkdocs-material with Sphinx + MyST + Shibuya, keeping all page content in Markdown, in a single clean-cutover branch (`feature/sphinx-docs`, already checked out off `main`).

**Architecture:** `docs/` stays the Sphinx source root. A new `docs/conf.py` drives the build. The two reference pages (`client/reference.md`, `cli/reference.md`) stay `.md` but embed short `` ```{eval-rst} `` blocks to call `autodoc`/`sphinx-click`, since those extensions have no native MyST syntax. `mkdocs.yml`, `overrides/`, and the old `docs` dependency group are deleted once everything is ported.

**Tech Stack:** Sphinx, myst-parser, sphinx-autobuild, shibuya (theme), sphinx-click, autodoc/autosummary (Sphinx core), uv.

## Global Constraints

- All page content stays in Markdown; RST is confined to `` ```{eval-rst} `` blocks inside `client/reference.md` and `cli/reference.md` only.
- Clean cutover: `mkdocs.yml`, `overrides/`, and the mkdocs-based `docs` dependency group must all be removed by the end of this plan — no dual-toolchain period.
- Final build must pass `sphinx-build -b html docs docs/_build/html -W` with zero warnings/errors.
- Theme is `shibuya`.
- `docs/` remains the source root; build output is `docs/_build/html` (already gitignored).
- `.github/workflows/docs.yml` must build with `sphinx-build` and upload `docs/_build/html` as the Pages artifact.

Spec: `docs/superpowers/specs/2026-07-07-sphinx-docs-migration-design.md`

---

### Task 1: Swap docs dependencies

**Files:**
- Modify: `pyproject.toml:68`

**Interfaces:**
- Produces: `sphinx`, `myst-parser`, `sphinx-autobuild`, `shibuya`, `sphinx-click` importable in the `docs` dependency group for all later tasks.

- [ ] **Step 1: Replace the `docs` dependency group**

In `pyproject.toml`, change:

```toml
docs = ["mkdocs-material", "mkdocstrings[python]", "mkdocs-click"]
```

to:

```toml
docs = ["sphinx", "myst-parser", "sphinx-autobuild", "shibuya", "sphinx-click"]
```

- [ ] **Step 2: Sync dependencies**

Run: `uv sync --group docs`
Expected: completes without error; `sphinx`, `myst-parser`, `sphinx_click`, `shibuya` are installed.

- [ ] **Step 3: Verify imports**

Run: `uv run python -c "import sphinx, myst_parser, sphinx_click, shibuya; print('ok')"`
Expected: prints `ok`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: swap mkdocs deps for sphinx/myst/shibuya"
```

---

### Task 2: Add base Sphinx configuration

**Files:**
- Create: `docs/conf.py`

**Interfaces:**
- Consumes: nothing from prior tasks.
- Produces: a working `sphinx-build` invocation for all later tasks to build against. Extensions enabled: `myst_parser`, `sphinx.ext.autodoc`, `sphinx.ext.autosummary`, `sphinx_click`.

- [ ] **Step 1: Create `docs/conf.py`**

```python
project = 'SJVAir Toolkit'
copyright = '2026, Central California Asthma Collaborative'
author = 'Central California Asthma Collaborative'

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx_click',
]

source_suffix = {
    '.md': 'markdown',
}

root_doc = 'index'

exclude_patterns = ['_build', 'superpowers']

autodoc_member_order = 'bysource'
autosummary_generate = True

html_theme = 'shibuya'
html_title = 'SJVAir Toolkit'
```

- [ ] **Step 2: Run a build and confirm Sphinx starts cleanly**

Run: `uv run sphinx-build -b html docs docs/_build/html`
Expected: the build completes (exit code 0) and `docs/_build/html/index.html` exists. Warnings about `::: sjvair...` blocks in the reference pages and about pages not being in a toctree are expected at this stage — those are fixed in Tasks 3–5. There should be **no Python traceback**.

- [ ] **Step 3: Commit**

```bash
git add docs/conf.py
git commit -m "feat: add base sphinx configuration"
```

---

### Task 3: Convert navigation to a MyST toctree

**Files:**
- Modify: `docs/index.md`

**Interfaces:**
- Consumes: `docs/conf.py` from Task 2 (`root_doc = 'index'`).
- Produces: working site navigation for all subsequent content tasks to build against.

- [ ] **Step 1: Add a hidden toctree to `docs/index.md`**

Append to the end of `docs/index.md` (content above is unchanged):

`````markdown

```{toctree}
:hidden:
:maxdepth: 2

cli/guide
cli/reference
client/guide
client/reference
changelog
```
`````

- [ ] **Step 2: Build and check for toctree warnings**

Run: `uv run sphinx-build -b html docs docs/_build/html`
Expected: no warnings of the form `document isn't included in any toctree` for `cli/guide`, `cli/reference`, `client/guide`, `client/reference`, or `changelog`. `docs/_build/html/cli/guide.html` exists and its sidebar contains links to all five pages.

- [ ] **Step 3: Commit**

```bash
git add docs/index.md
git commit -m "feat: convert docs nav to a MyST toctree"
```

---

### Task 4: Convert the Python API reference to autodoc

**Files:**
- Modify: `docs/client/reference.md`

**Interfaces:**
- Consumes: `sphinx.ext.autodoc` enabled in Task 2's `conf.py`.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Replace mkdocstrings blocks with `eval-rst`/`autoclass`/`automodule`**

Replace the full contents of `docs/client/reference.md` with:

`````markdown
# API reference

Auto-generated from docstrings.

## Client

```{eval-rst}
.. autoclass:: sjvair.client.SJVAirClient
   :members:
```

## Resources

```{eval-rst}
.. autoclass:: sjvair.resources.monitors.MonitorsResource
   :members:

.. autoclass:: sjvair.resources.regions.RegionsResource
   :members:

.. autoclass:: sjvair.resources.calenviroscreen.CalEnviroScreenResource
   :members:

.. autoclass:: sjvair.resources.ceidars.CEIDARSResource
   :members:

.. autoclass:: sjvair.resources.hms.HMSResource
   :members:

.. autoclass:: sjvair.resources.pesticides.PesticidesResource
   :members:
```

## Maps

Rendering utilities behind `sjvair map`/`sjvair timelapse` — requires `pip install sjvair[maps]` to actually render (importing the module does not).

```{eval-rst}
.. automodule:: sjvair.maps
   :members:
```
`````

- [ ] **Step 2: Build and verify the API reference renders**

Run: `uv run sphinx-build -b html docs docs/_build/html`
Expected: no errors from the `autoclass`/`automodule` directives (an import error here means `sjvair` isn't installed in the docs env — if so run `uv sync --group docs` again, since `uv sync` installs the project itself alongside dependency groups).

Run: `grep -o 'current_at' docs/_build/html/client/reference.html | head -1`
Expected: prints `current_at` (confirms `MonitorsResource.current_at` was picked up by autodoc).

- [ ] **Step 3: Commit**

```bash
git add docs/client/reference.md
git commit -m "feat: convert API reference to sphinx autodoc"
```

---

### Task 5: Convert the CLI reference to sphinx-click

**Files:**
- Modify: `docs/cli/reference.md`

**Interfaces:**
- Consumes: `sphinx_click` extension enabled in Task 2's `conf.py`.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Replace the mkdocs-click block with `eval-rst`/`click`**

Replace the full contents of `docs/cli/reference.md` with:

`````markdown
# CLI reference

Auto-generated from the `sjvair` command-line application.

```{eval-rst}
.. click:: sjvair.cli.main:cli
   :prog: sjvair
   :nested: full
```
`````

- [ ] **Step 2: Build and verify the command tree renders**

Run: `uv run sphinx-build -b html docs docs/_build/html`
Expected: no errors from the `click` directive.

Run: `grep -o 'timelapse' docs/_build/html/cli/reference.html | head -1`
Expected: prints `timelapse` (confirms the `timelapse` subcommand was picked up).

- [ ] **Step 3: Commit**

```bash
git add docs/cli/reference.md
git commit -m "feat: convert CLI reference to sphinx-click"
```

---

### Task 6: Convert the changelog to a MyST include

**Files:**
- Modify: `docs/changelog.md`

**Interfaces:**
- Consumes: nothing beyond core MyST parsing.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Replace the pymdownx snippet include with a MyST include**

Replace the full contents of `docs/changelog.md` with:

`````markdown
# Changelog

```{include} ../CHANGELOG.md
```
`````

- [ ] **Step 2: Build and verify the changelog content renders**

Run: `uv run sphinx-build -b html docs docs/_build/html`
Expected: no errors.

Run: `grep -o 'Keep a Changelog' docs/_build/html/changelog.html | head -1`
Expected: prints `Keep a Changelog` (confirms `CHANGELOG.md` content was included).

- [ ] **Step 3: Commit**

```bash
git add docs/changelog.md
git commit -m "feat: include root CHANGELOG.md via MyST include directive"
```

---

### Task 7: Port static assets, favicon, and extra meta tags

**Files:**
- Modify: `docs/conf.py`
- Create: `docs/_templates/layout.html`

**Interfaces:**
- Consumes: `docs/assets/` and `docs/stylesheets/extra.css` (unchanged, already in the repo).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Add static path, favicon, logo, and CSS config to `docs/conf.py`**

Append to `docs/conf.py`:

```python
templates_path = ['_templates']

html_static_path = ['assets', 'stylesheets']
html_css_files = ['extra.css']
html_favicon = 'assets/favicon/favicon.ico'
html_logo = 'assets/logo.svg'
```

- [ ] **Step 2: Create `docs/_templates/layout.html` for the extra meta tags**

This replicates `overrides/main.html`'s `extrahead` block, which mkdocs-material used for the apple-touch-icon, manifest, and Windows tile meta tags that `html_favicon` alone doesn't cover.

```html
{% extends "!layout.html" %}
{% block extrahead %}
  {{ super() }}
  <link rel="apple-touch-icon" sizes="180x180" href="{{ pathto('_static/favicon/apple-touch-icon.png', 1) }}">
  <link rel="icon" type="image/png" sizes="32x32" href="{{ pathto('_static/favicon/favicon-32x32.png', 1) }}">
  <link rel="icon" type="image/png" sizes="16x16" href="{{ pathto('_static/favicon/favicon-16x16.png', 1) }}">
  <link rel="manifest" href="{{ pathto('_static/favicon/site.webmanifest', 1) }}">
  <meta name="msapplication-config" content="{{ pathto('_static/favicon/browserconfig.xml', 1) }}">
  <meta name="msapplication-TileColor" content="#276eaf">
  <meta name="theme-color" content="#276eaf">
{% endblock %}
```

- [ ] **Step 3: Build and verify assets and meta tags are present**

Run: `uv run sphinx-build -b html docs docs/_build/html`
Expected: no errors.

Run: `grep -c 'apple-touch-icon\|msapplication-TileColor\|theme-color' docs/_build/html/index.html`
Expected: a non-zero count.

Run: `ls docs/_build/html/_static/extra.css docs/_build/html/_static/favicon.ico docs/_build/html/_static/logo.svg`
Expected: all three files listed (confirms `html_static_path` copied them).

- [ ] **Step 4: Manual visual check**

Open `docs/_build/html/index.html` in a browser and confirm: the favicon shows in the browser tab, and the SJVAir logo appears in the page header/sidebar.

- [ ] **Step 5: Commit**

```bash
git add docs/conf.py docs/_templates/layout.html
git commit -m "feat: port favicon, logo, and extra meta tags to sphinx"
```

---

### Task 8: Remove mkdocs configuration

**Files:**
- Delete: `mkdocs.yml`
- Delete: `overrides/main.html`
- Delete: `overrides/` (directory, now empty)

**Interfaces:**
- Consumes: Task 7 having ported everything `overrides/main.html` did.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Delete the old mkdocs config and overrides**

```bash
git rm mkdocs.yml overrides/main.html
rmdir overrides
```

- [ ] **Step 2: Confirm nothing else references them**

Run: `grep -rn "mkdocs\|overrides/" --include='*.toml' --include='*.yml' --include='*.yaml' . 2>/dev/null | grep -v '.venv\|_build'`
Expected: no output.

- [ ] **Step 3: Rebuild to confirm nothing broke**

Run: `uv run sphinx-build -b html docs docs/_build/html`
Expected: completes without error.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove mkdocs config and theme overrides"
```

---

### Task 9: Update the GitHub Pages workflow and run the final strict build

**Files:**
- Modify: `.github/workflows/docs.yml`

**Interfaces:**
- Consumes: everything from Tasks 1–8; this is the final acceptance gate for the whole plan.
- Produces: nothing (terminal task).

- [ ] **Step 1: Update the build step and artifact path**

In `.github/workflows/docs.yml`, change:

```yaml
      - run: uv sync --group docs
      - run: uv run mkdocs build --strict
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
```

to:

```yaml
      - run: uv sync --group docs
      - run: uv run sphinx-build -b html docs docs/_build/html -W
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs/_build/html
```

- [ ] **Step 2: Run the exact CI build command locally**

Run: `rm -rf docs/_build && uv run sphinx-build -b html docs docs/_build/html -W`
Expected: exit code 0, zero warnings, zero errors. This is the plan's final acceptance criterion — if it fails, the warning message names the file and line to fix.

- [ ] **Step 3: Smoke-test the dev server**

Run: `uv run sphinx-autobuild docs docs/_build/html --port 8080 &` then `sleep 2 && curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/` then kill the background process.
Expected: HTTP status `200`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/docs.yml
git commit -m "ci: build docs with sphinx instead of mkdocs"
```

---

## Final Acceptance Checklist

- [ ] `sphinx-build -b html docs docs/_build/html -W` exits 0 with zero warnings
- [ ] All 5 content pages reachable from the sidebar nav
- [ ] `client/reference.html` lists every class from the old mkdocstrings page, including `current_at`
- [ ] `cli/reference.html` lists the full `sjvair` command tree, including `timelapse`
- [ ] `changelog.html` renders the root `CHANGELOG.md` content
- [ ] `mkdocs.yml` and `overrides/` no longer exist in the repo
- [ ] `pyproject.toml`'s `docs` group contains no mkdocs packages
- [ ] `sphinx-autobuild` serves the site locally
