from django import template

register = template.Library()


@register.filter(name='add_class')
def add_class(field, css):
    """Add CSS class(es) to a BoundField when rendering.

    Usage in template: {{ form.field|add_class:'form-control' }}
    """
    try:
        return field.as_widget(attrs={**getattr(field.field.widget, 'attrs', {}), 'class': css})
    except Exception:
        return field
