from django.shortcuts import get_object_or_404, render

from pharmacy.models import Medicine


def product_detail(request, product_id):
    """Product detail page with related products"""
    product = get_object_or_404(Medicine, id=product_id, is_active=True)

    # Log product view for history (Task #7)
    if request.user.is_authenticated:
        from pharmacy.models.misc import ProductViewHistory

        ProductViewHistory.objects.create(user=request.user, product=product)

    # Get related products (same category, different product)
    related_products = Medicine.objects.filter(category=product.category, is_active=True, stock__gt=0).exclude(
        id=product.id
    )[:12]

    # Safely resolve main image URL — field may have a name but no file on disk
    DEFAULT_IMAGE = "/static/images/default/default_avatar.png"
    try:
        main_image_url = product.main_image.url if product.main_image and product.main_image.name else DEFAULT_IMAGE
    except (ValueError, AttributeError):
        main_image_url = DEFAULT_IMAGE

    context = {
        "product": product,
        "related_products": related_products,
        "is_authenticated": request.user.is_authenticated,
        "main_image_url": main_image_url,
    }

    return render(request, "product_detail.html", context)


def product_full_guide(request, product_id):
    """Full product guide page (instruction, side effects, contraindications, etc.)"""
    product = get_object_or_404(Medicine, id=product_id, is_active=True)

    context = {
        "product": product,
    }

    return render(request, "product_full_guide.html", context)
