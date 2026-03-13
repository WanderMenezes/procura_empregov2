from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def query_string(context, page=None):
    request = context.get('request')
    if not request:
        return ''
    params = request.GET.copy()
    # remove existing page param
    if 'page' in params:
        params.pop('page')
    if page is not None:
        params['page'] = page
    qs = params.urlencode()
    return ('?' + qs) if qs else ''
