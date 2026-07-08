import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent / '_ext'))

from openapi_renderer import DropdownHttpdomainRenderer  # noqa: E402

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
    'sphinx_design',
]

source_suffix = {
    '.md': 'markdown',
}

myst_heading_anchors = 3

root_doc = 'index'

exclude_patterns = ['_build', 'superpowers', 'api/_generated']

# openapi_renderers holds a class object, which Sphinx can't pickle for its
# config-value cache -- a build-speed optimization only, not a correctness
# issue, so the resulting warning is safe to suppress.
suppress_warnings = ['config.cache']

openapi_renderers = {'dropdown': DropdownHttpdomainRenderer}
openapi_default_renderer = 'dropdown'

OPENAPI_SPEC_URL = 'https://www.sjvair.com/api/2.0/openapi.json'
OPENAPI_GENERATED_DIR = Path(__file__).parent / 'api' / '_generated'


def _flatten_nullable_types(node):
    """Collapse OpenAPI 3.1 `type: [X, "null"]` into a single type.

    sphinxcontrib-openapi's generate-examples-from-schemas crashes on JSON
    Schema 2020-12 style type unions (TypeError: unhashable type: 'list'),
    which is how the live spec expresses nullable fields. This keeps the
    non-null type and drops "null" from the list so example generation has
    a concrete type to work with; nullability is still documented separately
    via each field's own description/required-ness.
    """
    if isinstance(node, dict):
        type_value = node.get('type')
        if isinstance(type_value, list):
            non_null = [t for t in type_value if t != 'null']
            node['type'] = non_null[0] if non_null else 'string'
        for value in node.values():
            _flatten_nullable_types(value)
    elif isinstance(node, list):
        for item in node:
            _flatten_nullable_types(item)


def fetch_openapi_spec(app):
    """Pull the live SJVAir API spec so the REST API reference is never stale.

    Failures degrade to a warning admonition instead of failing the build or
    falling back to a stale committed copy -- see docs/api/reference.md.
    """
    OPENAPI_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    spec_path = OPENAPI_GENERATED_DIR / 'openapi.json'
    body_path = OPENAPI_GENERATED_DIR / 'openapi.md'

    try:
        response = requests.get(OPENAPI_SPEC_URL, timeout=10)
        response.raise_for_status()
        spec = response.json()
        _flatten_nullable_types(spec)
        spec_path.write_text(json.dumps(spec))
        body_path.write_text(
            '```{eval-rst}\n'
            '.. openapi:: _generated/openapi.json\n'
            '   :generate-examples-from-schemas:\n'
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
