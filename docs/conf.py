from pathlib import Path

import requests

project = 'SJVAir Toolkit'
copyright = '2026, Central California Asthma Collaborative'
author = 'Central California Asthma Collaborative'

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
    'sphinx_click',
    'sphinxcontrib.openapi',
]

source_suffix = {
    '.md': 'markdown',
}

myst_heading_anchors = 3

root_doc = 'index'

exclude_patterns = ['_build', 'superpowers', 'api/_generated']

OPENAPI_SPEC_URL = 'https://www.sjvair.com/api/2.0/openapi.json'
OPENAPI_GENERATED_DIR = Path(__file__).parent / 'api' / '_generated'


def fetch_openapi_spec(app):
    """Pull the live SJVAir API spec so the REST API reference is never stale.

    Failures degrade to a warning admonition instead of failing the build or
    falling back to a stale committed copy -- see docs/api/reference.md.
    """
    OPENAPI_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    spec_path = OPENAPI_GENERATED_DIR / 'openapi.json'
    body_path = OPENAPI_GENERATED_DIR / 'body.md'

    try:
        response = requests.get(OPENAPI_SPEC_URL, timeout=10)
        response.raise_for_status()
        spec_path.write_text(response.text)
        body_path.write_text(
            '```{eval-rst}\n'
            '.. openapi:: _generated/openapi.json\n'
            '```\n'
        )
    except requests.exceptions.RequestException as exc:
        body_path.write_text(
            '```{warning}\n'
            f'Unable to fetch the live OpenAPI spec from sjvair.com for this build ({exc}). '
            'Check your network connection. The rest of the documentation built normally.\n'
            '```\n'
        )


def setup(app):
    app.connect('builder-inited', fetch_openapi_spec)

autodoc_member_order = 'bysource'
autosummary_generate = False

html_theme = 'shibuya'
html_title = 'SJVAir Toolkit'

templates_path = ['_templates']

html_static_path = ['_static']
html_css_files = ['extra.css']
html_favicon = '_static/favicon/favicon.ico'

html_theme_options = {
    'accent_color': 'blue',
    'light_logo': '_static/logo-color.svg',
    'dark_logo': '_static/logo-white.svg',

    "github_url": "https://github.com/sjvair/sjvair-python"
}
