from django import template

register = template.Library()

DEFAULT_AVATAR = "/static/images/default/default_avatar.png"
DEFAULT_PRODUCT = "/static/images/default/default_product.png"
DEFAULT_ICON = "/static/images/default/default_icon.png"


@register.filter(name="safe_image_url")
def safe_image_url(field, default=DEFAULT_PRODUCT):
    """
    Safely returns the URL of an ImageField/FileField.
    Returns `default` if the field is empty, None, or has no associated file on disk.

    Usage in template:
        {{ product.main_image|safe_image_url }}
        {{ product.image|safe_image_url:'/static/images/default/default_avatar.png' }}
    """
    if not field:
        return default
    try:
        if hasattr(field, "name") and not field.name:
            return default
        url = field.url
        return url if url else default
    except (ValueError, AttributeError):
        return default


@register.filter(name="default_product_image")
def default_product_image(field):
    """Shortcut for product images - uses default_product.png"""
    return safe_image_url(field, DEFAULT_PRODUCT)


@register.filter(name="default_avatar_image")
def default_avatar_image(field):
    """Shortcut for avatar images - uses default_avatar.png"""
    return safe_image_url(field, DEFAULT_AVATAR)
