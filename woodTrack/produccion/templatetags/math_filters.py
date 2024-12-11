from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplica el valor dado por el argumento."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return None
