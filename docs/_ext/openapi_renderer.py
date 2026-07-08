"""Custom sphinxcontrib-openapi renderer: dropdown-wrapped endpoints grouped by tag.

Groups endpoints under a real heading per OpenAPI tag (so Shibuya's "On this
page" sidebar becomes a de facto submenu), collapses each endpoint into a
sphinx-design dropdown with a compact method badge, and splits the endpoint
body into Parameters / Request body / Response tabs using sphinx-tabs
(Shibuya ships dedicated CSS for sphinx-tabs' ARIA-based markup; its
sphinx-design tab support is comparatively bare and had a layout bug where
the (should be invisible) radio input that drives each sphinx-design tab
took up its own row instead of overlapping its label). Each tab's content
is still produced by HttpdomainRenderer's own render_parameters() /
render_request_body() / render_responses() unchanged -- only how those
pieces are assembled is different, so parameter lists, response schemas,
and generated examples all behave exactly as before.
"""

from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx_tabs.tabs import SphinxTabsTab
from sphinxcontrib.openapi.renderers import HttpdomainRenderer
from sphinxcontrib.openapi.renderers._httpdomain import _iterinorder, indented


class RestoreSphinxTabsTabClass(SphinxPostTransform):
    """Undo a sphinx-design bug that clobbers sphinx-tabs' tab-button class.

    sphinx-design's dropdown post-transform (DropdownHtmlTransform,
    priority 199), when using card styling, replaces the `classes` of
    every nodes.paragraph descendant with just ["sd-card-text"]:

        para["classes"] = ([] if "classes" in para else para["classes"]) + ["sd-card-text"]

    That condition is inverted -- every docutils node has a `classes`
    list, so the `[]` branch always runs, discarding whatever classes
    were already there instead of preserving them. sphinx-tabs' tab
    button (SphinxTabsTab) is itself a nodes.paragraph subclass (it just
    renders as <button>), so nesting tabs inside a dropdown loses the
    "sphinx-tabs-tab" class every tab stylesheet (sphinx-tabs' own and
    Shibuya's) targets. Runs at a higher priority so it fires after
    DropdownHtmlTransform.
    """

    default_priority = 200

    def run(self, **kwargs):
        for node in self.document.findall(SphinxTabsTab):
            if 'sphinx-tabs-tab' not in node['classes']:
                node['classes'] = ['sphinx-tabs-tab']


_METHOD_COLORS = {
    'get': 'success',
    'post': 'primary',
    'put': 'warning',
    'patch': 'warning',
    'delete': 'danger',
}

# Tags whose display title doesn't follow from naive .title()-casing --
# matches the capitalization already used elsewhere in these docs (e.g.
# client/reference.md, cli/guide.md).
_TAG_TITLES = {
    'hms': 'HMS',
    'ceidars': 'CEIDARS',
    'calenviroscreen': 'CalEnviroScreen',
}


def _tag_title(tag):
    return _TAG_TITLES.get(tag, tag.replace('_', ' ').replace('-', ' ').title())


class DropdownHttpdomainRenderer(HttpdomainRenderer):
    """Groups operations by tag, rendering each as a collapsed dropdown."""

    def render_paths(self, paths):
        grouped = {}

        for endpoint, path in paths.items():
            common_parameters = path.pop('parameters', [])
            for key in {'summary', 'description', 'servers'}:
                path.pop(key, None)

            for method in _iterinorder(path, self._http_methods_order):
                operation = path[method]
                operation.setdefault('parameters', [])
                operation_parameters_ids = {
                    (parameter['name'], parameter['in'])
                    for parameter in operation['parameters']
                }
                operation['parameters'] = [
                    parameter
                    for parameter in common_parameters
                    if (parameter['name'], parameter['in']) not in operation_parameters_ids
                ] + operation['parameters']

                tag = (operation.get('tags') or ['Other'])[0]
                grouped.setdefault(tag, []).append((endpoint, method, operation))

        for tag, operations in grouped.items():
            title = _tag_title(tag)
            yield title
            yield '=' * len(title)
            yield ''

            for endpoint, method, operation in operations:
                color = _METHOD_COLORS.get(method, 'secondary')
                badge = f':bdg-{color}:`{method.upper()}`'
                dropdown_title = f'{badge} {endpoint}'
                if operation.get('summary'):
                    dropdown_title += f" — {operation['summary']}"

                yield f'.. dropdown:: {dropdown_title}'
                yield f'   :name: {method} {endpoint}'
                yield ''
                yield from indented(self.render_operation(endpoint, method, operation))
                yield ''

    def render_operation(self, endpoint, method, operation):
        """Render one operation with Parameters/Request body/Response as tabs.

        Sphinx's field-list-merging transform (the thing that turns
        `:queryparam x:` + `:queryparamtype x:` into a readable "x (type)"
        entry) only processes field lists that are *immediate* children of
        an `.. http:get::` directive's own content -- by explicit design,
        it does not traverse into nested containers like a sphinx-tabs
        `tab`. So each tab gets its own `.. http:get::` block (making its
        field list a direct child again); all but the first are `:noindex:`
        so the endpoint is only registered once in the search index /
        routing table / cross-reference targets.
        """
        body = []

        if operation.get('summary'):
            body.append(f"**{operation['summary']}**")
            body.append('')

        if operation.get('description'):
            body.extend(self._convert_markup(operation['description']).strip().splitlines())
            body.append('')

        tabs = []

        parameter_lines = list(self.render_parameters(operation.get('parameters', [])))
        if parameter_lines:
            tabs.append(('Parameters', parameter_lines))

        if 'requestBody' in operation:
            request_lines = list(
                self.render_request_body(operation['requestBody'], endpoint, method)
            )
            if request_lines:
                tabs.append(('Request body', request_lines))

        response_lines = list(self.render_responses(operation['responses']))
        if response_lines:
            tabs.append(('Response', response_lines))

        def http_block(lines, noindex):
            block = [f'.. http:{method}:: {endpoint}']
            if noindex:
                block.append('   :noindex:')
            if operation.get('deprecated'):
                block.append('   :deprecated:')
            block.append('')
            block.extend(indented(lines))
            return block

        if tabs:
            body.append('.. tabs::')
            body.append('')
            for index, (title, lines) in enumerate(tabs):
                body.append(f'   .. tab:: {title}')
                body.append('')
                body.extend(indented(indented(http_block(lines, noindex=index != 0))))
                body.append('')
        else:
            body.extend(http_block([], noindex=False))

        yield from body
