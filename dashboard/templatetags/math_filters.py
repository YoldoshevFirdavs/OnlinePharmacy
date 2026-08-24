"""
Custom template filters for mathematical operations.
"""

from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def multiply(value, arg):
    """Multiply two numbers."""
    try:
        value = Decimal(str(value))
        arg = Decimal(str(arg))
        return value * arg
    except (ValueError, TypeError):
        return 0


@register.filter
def replace(value, arg):
    """Replace substring in string. Usage: {{ value|replace:'old':'new' }}"""
    if not isinstance(value, str):
        value = str(value)

    if ":" not in arg:
        return value

    old, new = arg.split(":", 1)
    return value.replace(old, new)


@register.filter
def user_avatar_url(user):
    """Get user avatar URL or default placeholder.
    Usage: {{ user|user_avatar_url }}
    Returns: URL string
    """
    if not user:
        return "/static/images/default/default_avatar.png"

    if hasattr(user, "avatar") and user.avatar:
        try:
            return user.avatar.url
        except (ValueError, AttributeError):
            return "/static/images/default/default_avatar.png"

    return "/static/images/default/default_avatar.png"
