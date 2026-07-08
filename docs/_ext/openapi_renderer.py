"""Custom sphinxcontrib-openapi renderer: dropdown-wrapped endpoints grouped by tag.

Phase 1 of the REST API reference's visual overhaul: group endpoints under a
real heading per OpenAPI tag (so Shibuya's "On this page" sidebar becomes a
de facto submenu) and collapse each endpoint into a colored sphinx-design
dropdown. Everything *inside* a dropdown is still produced by
HttpdomainRenderer's own render_operation() unchanged, so parameter lists,
response schemas, and generated examples behave exactly as before -- only
the grouping and collapsing wrapper is new.
"""

from sphinxcontrib.openapi.renderers import HttpdomainRenderer
from sphinxcontrib.openapi.renderers._httpdomain import _iterinorder, indented

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
                yield ''
                yield from indented(self.render_operation(endpoint, method, operation))
                yield ''
