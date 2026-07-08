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
