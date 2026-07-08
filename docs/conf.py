project = 'SJVAir Toolkit'
copyright = '2026, Central California Asthma Collaborative'
author = 'Central California Asthma Collaborative'

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
    'sphinx_click',
]

source_suffix = {
    '.md': 'markdown',
}

myst_heading_anchors = 3

root_doc = 'index'

exclude_patterns = ['_build', 'superpowers']

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
