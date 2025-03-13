from django import template

register = template.Library()

@register.filter
def lookup(value, key):
    """Helper filter to access dictionary or object attributes dynamically."""
    if isinstance(value, dict):
        return value.get(key, [])
    return getattr(value, key, [])

@register.filter
def range_filter(block):
    """Generate a range of indices for a matching block."""
    return range(block.a, block.a + block.size) if hasattr(block, 'a') else range(block.b, block.b + block.size)

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''