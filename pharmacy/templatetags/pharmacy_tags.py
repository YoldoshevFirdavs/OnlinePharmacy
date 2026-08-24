from django import template

register = template.Library()

DEFAULT_IMAGE = "/static/images/default/default_avatar.png"


@register.filter(name="safe_image_url")
def safe_image_url(field, default=DEFAULT_IMAGE):
    """
    Safely returns the URL of an ImageField/FileField.
    Returns `default` if the field is empty, None, or has no associated file on disk.

    Usage in template:
        {{ product.main_image|safe_image_url }}
        {{ product.image|safe_image_url:'/static/images/placeholder.png' }}
    """
    if not field:
        return default
    try:
        url = field.url
        return url if url else default
    except (ValueError, AttributeError):
        return default
